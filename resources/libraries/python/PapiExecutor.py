# Copyright (c) 2020 Cisco and/or its affiliates.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Python API executor library.
"""

import copy
import glob
import json
import shutil
import struct  # vpp-papi can raise struct.error
import subprocess
import sys
import tempfile
import time

from pprint import pformat
from robot.api import logger

from resources.libraries.python.Constants import Constants
from resources.libraries.python.LocalExecution import run
from resources.libraries.python.FilteredLogger import FilteredLogger
from resources.libraries.python.PapiHistory import PapiHistory
from resources.libraries.python.ssh import (
    SSH, SSHTimeout, exec_cmd_no_error, scp_node)
from resources.libraries.python.topology import Topology, SocketType
from resources.libraries.python.VppApiCrc import VppApiCrcChecker


__all__ = [u"PapiExecutor", u"PapiSocketExecutor"]


def dictize(obj):
    """A helper method, to make namedtuple-like object accessible as dict.

    If the object is namedtuple-like, its _asdict() form is returned,
    but in the returned object __getitem__ method is wrapped
    to dictize also any items returned.
    If the object does not have _asdict, it will be returned without any change.
    Integer keys still access the object as tuple.

    A more useful version would be to keep obj mostly as a namedtuple,
    just add getitem for string keys. Unfortunately, namedtuple inherits
    from tuple, including its read-only __getitem__ attribute,
    so we cannot monkey-patch it.

    TODO: Create a proxy for named tuple to allow that.

    :param obj: Arbitrary object to dictize.
    :type obj: object
    :returns: Dictized object.
    :rtype: same as obj type or collections.OrderedDict
    """
    if not hasattr(obj, u"_asdict"):
        return obj
    ret = obj._asdict()
    old_get = ret.__getitem__
    new_get = lambda self, key: dictize(old_get(self, key))
    ret.__getitem__ = new_get
    return ret


class PapiSocketExecutor:
    """Methods for executing VPP Python API commands on forwarded socket.

    The current implementation connects for the duration of resource manager.
    Delay for accepting connection is 10s, and disconnect is explicit.
    TODO: Decrease 10s to value that is long enough for creating connection
    and short enough to not affect performance.

    The current implementation downloads and parses .api.json files only once
    and stores a VPPApiClient instance (disconnected) as a class variable.
    Accessing multiple nodes with different APIs is therefore not supported.

    The current implementation seems to run into read error occasionally.
    Not sure if the error is in Python code on Robot side, ssh forwarding,
    or socket handling at VPP side. Anyway, reconnect after some sleep
    seems to help, hoping repeated command execution does not lead to surprises.
    The reconnection is logged at WARN level, so it is prominently shown
    in log.html, so we can see how frequently it happens.

    TODO: Support handling of retval!=0 without try/except in caller.

    Note: Use only with "with" statement, e.g.:

        cmd = 'show_version'
        with PapiSocketExecutor(node) as papi_exec:
            reply = papi_exec.add(cmd).get_reply(err_msg)

    This class processes two classes of VPP PAPI methods:
    1. Simple request / reply: method='request'.
    2. Dump functions: method='dump'.

    Note that access to VPP stats over socket is not supported yet.

    The recommended ways of use are (examples):

    1. Simple request / reply

    a. One request with no arguments:

        cmd = 'show_version'
        with PapiSocketExecutor(node) as papi_exec:
            reply = papi_exec.add(cmd).get_reply(err_msg)

    b. Three requests with arguments, the second and the third ones are the same
       but with different arguments.

        with PapiSocketExecutor(node) as papi_exec:
            replies = papi_exec.add(cmd1, **args1).add(cmd2, **args2).\
                add(cmd2, **args3).get_replies(err_msg)

    2. Dump functions

        cmd = 'sw_interface_rx_placement_dump'
        with PapiSocketExecutor(node) as papi_exec:
            details = papi_exec.add(cmd, sw_if_index=ifc['vpp_sw_index']).\
                get_details(err_msg)
    """

    # Class cache for reuse between instances.
    vpp_instance = None
    """Takes long time to create, stores all PAPI functions and types."""
    crc_checker = None
    """Accesses .api.json files at creation, caching allows deleting them."""

    def __init__(self, node, remote_vpp_socket=Constants.SOCKSVR_PATH):
        """Store the given arguments, declare managed variables.

        :param node: Node to connect to and forward unix domain socket from.
        :param remote_vpp_socket: Path to remote socket to tunnel to.
        :type node: dict
        :type remote_vpp_socket: str
        """
        self._node = node
        self._remote_vpp_socket = remote_vpp_socket
        # The list of PAPI commands to be executed on the node.
        self._api_command_list = list()
        # The following values are set on enter, reset on exit.
        self._temp_dir = None
        self._ssh_control_socket = None
        self._local_vpp_socket = None
        self.initialize_vpp_instance()

    def initialize_vpp_instance(self):
        """Create VPP instance with bindings to API calls, store as class field.

        No-op if the instance had been stored already.

        The instance is initialized for unix domain socket access,
        it has initialized all the bindings, but it is not connected
        (to a local socket) yet.

        This method downloads .api.json files from self._node
        into a temporary directory, deletes them finally.
        """
        if self.vpp_instance:
            return
        cls = self.__class__  # Shorthand for setting class fields.
        package_path = None
        tmp_dir = tempfile.mkdtemp(dir=u"/tmp")
        try:
            # Pack, copy and unpack Python part of VPP installation from _node.
            # TODO: Use rsync or recursive version of ssh.scp_node instead?
            node = self._node
            exec_cmd_no_error(node, [u"rm", u"-rf", u"/tmp/papi.txz"])
            # Papi python version depends on OS (and time).
            # Python 2.7 or 3.4, site-packages or dist-packages.
            installed_papi_glob = u"/usr/lib/python3*/*-packages/vpp_papi"
            # We need to wrap this command in bash, in order to expand globs,
            # and as ssh does join, the inner command has to be quoted.
            inner_cmd = u" ".join([
                u"tar", u"cJf", u"/tmp/papi.txz", u"--exclude=*.pyc",
                installed_papi_glob, u"/usr/share/vpp/api"
            ])
            exec_cmd_no_error(node, [u"bash", u"-c", u"'" + inner_cmd + u"'"])
            scp_node(node, tmp_dir + u"/papi.txz", u"/tmp/papi.txz", get=True)
            run([u"tar", u"xf", tmp_dir + u"/papi.txz", u"-C", tmp_dir])
            api_json_directory = tmp_dir + u"/usr/share/vpp/api"
            # Perform initial checks before .api.json files are gone,
            # by creating the checker instance.
            cls.crc_checker = VppApiCrcChecker(api_json_directory)
            # When present locally, we finally can find the installation path.
            package_path = glob.glob(tmp_dir + installed_papi_glob)[0]
            # Package path has to be one level above the vpp_papi directory.
            package_path = package_path.rsplit(u"/", 1)[0]
            sys.path.append(package_path)
            # TODO: Pylint says import-outside-toplevel and import-error.
            # It is right, we should refactor the code and move initialization
            # of package outside.
            from vpp_papi.vpp_papi import VPPApiClient as vpp_class
            vpp_class.apidir = api_json_directory
            # We need to create instance before removing from sys.path.
            cls.vpp_instance = vpp_class(
                use_socket=True, server_address=u"TBD", async_thread=False,
                read_timeout=14, logger=FilteredLogger(logger, u"INFO"))
            # Cannot use loglevel parameter, robot.api.logger lacks support.
            # TODO: Stop overriding read_timeout when VPP-1722 is fixed.
        finally:
            shutil.rmtree(tmp_dir)
            if sys.path[-1] == package_path:
                sys.path.pop()

    def __enter__(self):
        """Create a tunnel, connect VPP instance.

        Only at this point a local socket names are created
        in a temporary directory, because VIRL runs 3 pybots at once,
        so harcoding local filenames does not work.

        :returns: self
        :rtype: PapiSocketExecutor
        """
        time_enter = time.time()
        # Parsing takes longer than connecting, prepare instance before tunnel.
        vpp_instance = self.vpp_instance
        node = self._node
        self._temp_dir = tempfile.mkdtemp(dir=u"/tmp")
        self._local_vpp_socket = self._temp_dir + u"/vpp-api.sock"
        self._ssh_control_socket = self._temp_dir + u"/ssh.sock"
        ssh_socket = self._ssh_control_socket
        # Cleanup possibilities.
        ret_code, _ = run([u"ls", ssh_socket], check=False)
        if ret_code != 2:
            # This branch never seems to be hit in CI,
            # but may be useful when testing manually.
            run(
                [u"ssh", u"-S", ssh_socket, u"-O", u"exit", u"0.0.0.0"],
                check=False, log=True
            )
            # TODO: Is any sleep necessary? How to prove if not?
            run([u"sleep", u"0.1"])
            run([u"rm", u"-vrf", ssh_socket])
        # Even if ssh can perhaps reuse this file,
        # we need to remove it for readiness detection to work correctly.
        run([u"rm", u"-rvf", self._local_vpp_socket])
        # We use sleep command. The ssh command will exit in 30 second,
        # unless a local socket connection is established,
        # in which case the ssh command will exit only when
        # the ssh connection is closed again (via control socket).
        # The log level is to suppress "Warning: Permanently added" messages.
        ssh_cmd = [
            u"ssh", u"-S", ssh_socket, u"-M",
            u"-o", u"LogLevel=ERROR", u"-o", u"UserKnownHostsFile=/dev/null",
            u"-o", u"StrictHostKeyChecking=no",
            u"-o", u"ExitOnForwardFailure=yes",
            u"-L", self._local_vpp_socket + u":" + self._remote_vpp_socket,
            u"-p", str(node[u"port"]), node[u"username"] + u"@" + node[u"host"],
            u"sleep", u"30"
        ]
        priv_key = node.get(u"priv_key")
        if priv_key:
            # This is tricky. We need a file to pass the value to ssh command.
            # And we need ssh command, because paramiko does not support sockets
            # (neither ssh_socket, nor _remote_vpp_socket).
            key_file = tempfile.NamedTemporaryFile()
            key_file.write(priv_key)
            # Make sure the content is written, but do not close yet.
            key_file.flush()
            ssh_cmd[1:1] = [u"-i", key_file.name]
        password = node.get(u"password")
        if password:
            # Prepend sshpass command to set password.
            ssh_cmd[:0] = [u"sshpass", u"-p", password]
        time_stop = time.time() + 10.0
        # subprocess.Popen seems to be the best way to run commands
        # on background. Other ways (shell=True with "&" and ssh with -f)
        # seem to be too dependent on shell behavior.
        # In particular, -f does NOT return values for run().
        subprocess.Popen(ssh_cmd)
        # Check socket presence on local side.
        while time.time() < time_stop:
            # It can take a moment for ssh to create the socket file.
            ret_code, _ = run(
                [u"ls", u"-l", self._local_vpp_socket], check=False
            )
            if not ret_code:
                break
            time.sleep(0.1)
        else:
            raise RuntimeError(u"Local side socket has not appeared.")
        if priv_key:
            # Socket up means the key has been read. Delete file by closing it.
            key_file.close()
        # Everything is ready, set the local socket address and connect.
        vpp_instance.transport.server_address = self._local_vpp_socket
        # It seems we can get read error even if every preceding check passed.
        # Single retry seems to help.
        for _ in range(2):
            try:
                vpp_instance.connect_sync(u"csit_socket")
            except (IOError, struct.error) as err:
                logger.warn(f"Got initial connect error {err!r}")
                vpp_instance.disconnect()
            else:
                break
        else:
            raise RuntimeError(u"Failed to connect to VPP over a socket.")
        logger.trace(
            f"Establishing socket connection took {time.time()-time_enter}s"
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Disconnect the vpp instance, tear down the SHH tunnel.

        Also remove the local sockets by deleting the temporary directory.
        Arguments related to possible exception are entirely ignored.
        """
        self.vpp_instance.disconnect()
        run([
            u"ssh", u"-S", self._ssh_control_socket, u"-O", u"exit", u"0.0.0.0"
        ], check=False)
        shutil.rmtree(self._temp_dir)

    def add(self, csit_papi_command, history=True, **kwargs):
        """Add next command to internal command list; return self.

        Unless disabled, new entry to papi history is also added at this point.
        The argument name 'csit_papi_command' must be unique enough as it cannot
        be repeated in kwargs.
        The kwargs dict is deep-copied, so it is safe to use the original
        with partial modifications for subsequent commands.

        Any pending conflicts from .api.json processing are raised.
        Then the command name is checked for known CRCs.
        Unsupported commands raise an exception, as CSIT change
        should not start using messages without making sure which CRCs
        are supported.
        Each CRC issue is raised only once, so subsequent tests
        can raise other issues.

        :param csit_papi_command: VPP API command.
        :param history: Enable/disable adding command to PAPI command history.
        :param kwargs: Optional key-value arguments.
        :type csit_papi_command: str
        :type history: bool
        :type kwargs: dict
        :returns: self, so that method chaining is possible.
        :rtype: PapiSocketExecutor
        :raises RuntimeError: If unverified or conflicting CRC is encountered.
        """
        self.crc_checker.report_initial_conflicts()
        if history:
            PapiHistory.add_to_papi_history(
                self._node, csit_papi_command, **kwargs
            )
        self.crc_checker.check_api_name(csit_papi_command)
        self._api_command_list.append(
            dict(
                api_name=csit_papi_command,
                api_args=copy.deepcopy(kwargs)
            )
        )
        return self

    def get_replies(self, err_msg="Failed to get replies."):
        """Get replies from VPP Python API.

        The replies are parsed into dict-like objects,
        "retval" field is guaranteed to be zero on success.

        :param err_msg: The message used if the PAPI command(s) execution fails.
        :type err_msg: str
        :returns: Responses, dict objects with fields due to API and "retval".
        :rtype: list of dict
        :raises RuntimeError: If retval is nonzero, parsing or ssh error.
        """
        return self._execute(err_msg=err_msg)

    def get_reply(self, err_msg=u"Failed to get reply."):
        """Get reply from VPP Python API.

        The reply is parsed into dict-like object,
        "retval" field is guaranteed to be zero on success.

        TODO: Discuss exception types to raise, unify with inner methods.

        :param err_msg: The message used if the PAPI command(s) execution fails.
        :type err_msg: str
        :returns: Response, dict object with fields due to API and "retval".
        :rtype: dict
        :raises AssertionError: If retval is nonzero, parsing or ssh error.
        """
        replies = self.get_replies(err_msg=err_msg)
        if len(replies) != 1:
            raise RuntimeError(f"Expected single reply, got {replies!r}")
        return replies[0]

    def get_sw_if_index(self, err_msg=u"Failed to get reply."):
        """Get sw_if_index from reply from VPP Python API.

        Frequently, the caller is only interested in sw_if_index field
        of the reply, this wrapper makes such call sites shorter.

        TODO: Discuss exception types to raise, unify with inner methods.

        :param err_msg: The message used if the PAPI command(s) execution fails.
        :type err_msg: str
        :returns: Response, sw_if_index value of the reply.
        :rtype: int
        :raises AssertionError: If retval is nonzero, parsing or ssh error.
        """
        reply = self.get_reply(err_msg=err_msg)
        logger.trace(f"Getting index from {reply!r}")
        return reply[u"sw_if_index"]

    def get_details(self, err_msg="Failed to get dump details."):
        """Get dump details from VPP Python API.

        The details are parsed into dict-like objects.
        The number of details per single dump command can vary,
        and all association between details and dumps is lost,
        so if you care about the association (as opposed to
        logging everything at once for debugging purposes),
        it is recommended to call get_details for each dump (type) separately.

        :param err_msg: The message used if the PAPI command(s) execution fails.
        :type err_msg: str
        :returns: Details, dict objects with fields due to API without "retval".
        :rtype: list of dict
        """
        return self._execute(err_msg)

    @staticmethod
    def run_cli_cmd(
            node, cli_cmd, log=True, remote_vpp_socket=Constants.SOCKSVR_PATH):
        """Run a CLI command as cli_inband, return the "reply" field of reply.

        Optionally, log the field value.

        :param node: Node to run command on.
        :param cli_cmd: The CLI command to be run on the node.
        :param remote_vpp_socket: Path to remote socket to tunnel to.
        :param log: If True, the response is logged.
        :type node: dict
        :type remote_vpp_socket: str
        :type cli_cmd: str
        :type log: bool
        :returns: CLI output.
        :rtype: str
        """
        cmd = u"cli_inband"
        args = dict(
            cmd=cli_cmd
        )
        err_msg = f"Failed to run 'cli_inband {cli_cmd}' PAPI command " \
            f"on host {node[u'host']}"

        with PapiSocketExecutor(node, remote_vpp_socket) as papi_exec:
            reply = papi_exec.add(cmd, **args).get_reply(err_msg)["reply"]
        if log:
            logger.info(
                f"{cli_cmd} ({node[u'host']} - {remote_vpp_socket}):\n"
                f"{reply.strip()}"
            )
        return reply

    @staticmethod
    def run_cli_cmd_on_all_sockets(node, cli_cmd, log=True):
        """Run a CLI command as cli_inband, on all sockets in topology file.

        :param node: Node to run command on.
        :param cli_cmd: The CLI command to be run on the node.
        :param log: If True, the response is logged.
        :type node: dict
        :type cli_cmd: str
        :type log: bool
        """
        sockets = Topology.get_node_sockets(node, socket_type=SocketType.PAPI)
        if sockets:
            for socket in sockets.values():
                PapiSocketExecutor.run_cli_cmd(
                    node, cli_cmd, log=log, remote_vpp_socket=socket
                )

    @staticmethod
    def dump_and_log(node, cmds):
        """Dump and log requested information, return None.

        :param node: DUT node.
        :param cmds: Dump commands to be executed.
        :type node: dict
        :type cmds: list of str
        """
        with PapiSocketExecutor(node) as papi_exec:
            for cmd in cmds:
                dump = papi_exec.add(cmd).get_details()
                logger.debug(f"{cmd}:\n{pformat(dump)}")

    def _execute(self, err_msg=u"Undefined error message", exp_rv=0):
        """Turn internal command list into data and execute; return replies.

        This method also clears the internal command list.

        IMPORTANT!
        Do not use this method in L1 keywords. Use:
        - get_replies()
        - get_reply()
        - get_sw_if_index()
        - get_details()

        :param err_msg: The message used if the PAPI command(s) execution fails.
        :type err_msg: str
        :returns: Papi responses parsed into a dict-like object,
            with fields due to API (possibly including retval).
        :rtype: list of dict
        :raises RuntimeError: If the replies are not all correct.
        """
        vpp_instance = self.vpp_instance
        local_list = self._api_command_list
        # Clear first as execution may fail.
        self._api_command_list = list()
        replies = list()
        for command in local_list:
            api_name = command[u"api_name"]
            papi_fn = getattr(vpp_instance.api, api_name)
            try:
                try:
                    reply = papi_fn(**command[u"api_args"])
                except (IOError, struct.error) as err:
                    # Occasionally an error happens, try reconnect.
                    logger.warn(f"Reconnect after error: {err!r}")
                    self.vpp_instance.disconnect()
                    # Testing shows immediate reconnect fails.
                    time.sleep(1)
                    self.vpp_instance.connect_sync(u"csit_socket")
                    logger.trace(u"Reconnected.")
                    reply = papi_fn(**command[u"api_args"])
            except (AttributeError, IOError, struct.error) as err:
                raise AssertionError(err_msg) from err
            # *_dump commands return list of objects, convert, ordinary reply.
            if not isinstance(reply, list):
                reply = [reply]
            for item in reply:
                self.crc_checker.check_api_name(item.__class__.__name__)
                dict_item = dictize(item)
                if u"retval" in dict_item.keys():
                    # *_details messages do not contain retval.
                    retval = dict_item[u"retval"]
                    if retval != exp_rv:
                        # TODO: What exactly to log and raise here?
                        raise AssertionError(
                            f"Retval {retval!r} does not match expected "
                            f"retval {exp_rv!r}"
                        )
                replies.append(dict_item)
        return replies


class PapiExecutor:
    """Contains methods for executing VPP Python API commands on DUTs.

    TODO: Remove .add step, make get_stats accept paths directly.

    This class processes only one type of VPP PAPI methods: vpp-stats.

    The recommended ways of use are (examples):

    path = ['^/if', '/err/ip4-input', '/sys/node/ip4-input']
    with PapiExecutor(node) as papi_exec:
        stats = papi_exec.add(api_name='vpp-stats', path=path).get_stats()

    print('RX interface core 0, sw_if_index 0:\n{0}'.\
        format(stats[0]['/if/rx'][0][0]))

    or

    path_1 = ['^/if', ]
    path_2 = ['^/if', '/err/ip4-input', '/sys/node/ip4-input']
    with PapiExecutor(node) as papi_exec:
        stats = papi_exec.add('vpp-stats', path=path_1).\
            add('vpp-stats', path=path_2).get_stats()

    print('RX interface core 0, sw_if_index 0:\n{0}'.\
        format(stats[1]['/if/rx'][0][0]))

    Note: In this case, when PapiExecutor method 'add' is used:
    - its parameter 'csit_papi_command' is used only to keep information
      that vpp-stats are requested. It is not further processed but it is
      included in the PAPI history this way:
      vpp-stats(path=['^/if', '/err/ip4-input', '/sys/node/ip4-input'])
      Always use csit_papi_command="vpp-stats" if the VPP PAPI method
      is "stats".
    - the second parameter must be 'path' as it is used by PapiExecutor
      method 'add'.
    """

    def __init__(self, node):
        """Initialization.

        :param node: Node to run command(s) on.
        :type node: dict
        """
        # Node to run command(s) on.
        self._node = node

        # The list of PAPI commands to be executed on the node.
        self._api_command_list = list()

        self._ssh = SSH()

    def __enter__(self):
        try:
            self._ssh.connect(self._node)
        except IOError:
            raise RuntimeError(
                f"Cannot open SSH connection to host {self._node[u'host']} "
                f"to execute PAPI command(s)"
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._ssh.disconnect(self._node)

    def add(self, csit_papi_command=u"vpp-stats", history=True, **kwargs):
        """Add next command to internal command list; return self.

        The argument name 'csit_papi_command' must be unique enough as it cannot
        be repeated in kwargs.
        The kwargs dict is deep-copied, so it is safe to use the original
        with partial modifications for subsequent commands.

        :param csit_papi_command: VPP API command.
        :param history: Enable/disable adding command to PAPI command history.
        :param kwargs: Optional key-value arguments.
        :type csit_papi_command: str
        :type history: bool
        :type kwargs: dict
        :returns: self, so that method chaining is possible.
        :rtype: PapiExecutor
        """
        if history:
            PapiHistory.add_to_papi_history(
                self._node, csit_papi_command, **kwargs
            )
        self._api_command_list.append(
            dict(
                api_name=csit_papi_command, api_args=copy.deepcopy(kwargs)
            )
        )
        return self

    def get_stats(
            self, err_msg=u"Failed to get statistics.", timeout=120,
            socket=Constants.SOCKSTAT_PATH):
        """Get VPP Stats from VPP Python API.

        :param err_msg: The message used if the PAPI command(s) execution fails.
        :param timeout: Timeout in seconds.
        :param socket: Path to Stats socket to tunnel to.
        :type err_msg: str
        :type timeout: int
        :type socket: str
        :returns: Requested VPP statistics.
        :rtype: list of dict
        """
        paths = [cmd[u"api_args"][u"path"] for cmd in self._api_command_list]
        self._api_command_list = list()

        stdout = self._execute_papi(
            paths, method=u"stats", err_msg=err_msg, timeout=timeout,
            socket=socket
        )

        return json.loads(stdout)

    @staticmethod
    def _process_api_data(api_d):
        """Process API data for smooth converting to JSON string.

        Apply binascii.hexlify() method for string values.

        :param api_d: List of APIs with their arguments.
        :type api_d: list
        :returns: List of APIs with arguments pre-processed for JSON.
        :rtype: list
        """

        def process_value(val):
            """Process value.

            :param val: Value to be processed.
            :type val: object
            :returns: Processed value.
            :rtype: dict or str or int
            """
            if isinstance(val, dict):
                for val_k, val_v in val.items():
                    val[str(val_k)] = process_value(val_v)
                retval = val
            elif isinstance(val, list):
                for idx, val_l in enumerate(val):
                    val[idx] = process_value(val_l)
                retval = val
            else:
                retval = val.encode().hex() if isinstance(val, str) else val
            return retval

        api_data_processed = list()
        for api in api_d:
            api_args_processed = dict()
            for a_k, a_v in api[u"api_args"].items():
                api_args_processed[str(a_k)] = process_value(a_v)
            api_data_processed.append(
                dict(
                    api_name=api[u"api_name"],
                    api_args=api_args_processed
                )
            )
        return api_data_processed

    def _execute_papi(
            self, api_data, method=u"request", err_msg=u"", timeout=120,
            socket=None):
        """Execute PAPI command(s) on remote node and store the result.

        :param api_data: List of APIs with their arguments.
        :param method: VPP Python API method. Supported methods are: 'request',
            'dump' and 'stats'.
        :param err_msg: The message used if the PAPI command(s) execution fails.
        :param timeout: Timeout in seconds.
        :type api_data: list
        :type method: str
        :type err_msg: str
        :type timeout: int
        :returns: Stdout from remote python utility, to be parsed by caller.
        :rtype: str
        :raises SSHTimeout: If PAPI command(s) execution has timed out.
        :raises RuntimeError: If PAPI executor failed due to another reason.
        :raises AssertionError: If PAPI command(s) execution has failed.
        """
        if not api_data:
            raise RuntimeError(u"No API data provided.")

        json_data = json.dumps(api_data) \
            if method in (u"stats", u"stats_request") \
            else json.dumps(self._process_api_data(api_data))

        sock = f" --socket {socket}" if socket else u""
        cmd = f"{Constants.REMOTE_FW_DIR}/{Constants.RESOURCES_PAPI_PROVIDER}" \
            f" --method {method} --data '{json_data}'{sock}"
        try:
            ret_code, stdout, _ = self._ssh.exec_command_sudo(
                cmd=cmd, timeout=timeout, log_stdout_err=False
            )
        # TODO: Fail on non-empty stderr?
        except SSHTimeout:
            logger.error(
                f"PAPI command(s) execution timeout on host "
                f"{self._node[u'host']}:\n{api_data}"
            )
            raise
        except Exception as exc:
            raise RuntimeError(
                f"PAPI command(s) execution on host {self._node[u'host']} "
                f"failed: {api_data}"
            ) from exc
        if ret_code != 0:
            raise AssertionError(err_msg)

        return stdout
