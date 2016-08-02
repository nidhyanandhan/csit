# Copyright (c) 2016 Cisco and/or its affiliates.
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

"""Dpdk Utilities Library."""

from resources.libraries.python.ssh import SSH, exec_cmd_no_error


class DpdkUtil(object):
    """Utilities for DPDK."""

    @staticmethod
    def dpdk_testpmd_start(node, **args):
        """Start DPDK testpmd app on VM node.

        :param node: VM Node to start testpmd on.
        :param args: List of testpmd parameters.
        :type node: dict
        :type args: list
        :return: nothing
        """
        # Set the hexadecimal bitmask of the cores to run on.
        eal_coremask = '-c {} '.format(args['eal_coremask'])\
            if args.get('eal_coremask', '') else ''
        # Set the number of memory channels to use.
        eal_mem_channels = '-n {} '.format(args['eal_mem_channels'])\
            if args.get('eal_mem_channels', '') else ''
        # Set the memory to allocate on specific sockets (comma separated).
        eal_socket_mem = '--socket-mem {} '.format(args['eal_socket_mem'])\
            if args.get('eal_socket_mem', '') else ''
        # Load an external driver. Multiple -d options are allowed.
        eal_driver = '-d /usr/lib/librte_pmd_virtio.so '
        # Set the forwarding mode: io, mac, mac_retry, mac_swap, flowgen,
        # rxonly, txonly, csum, icmpecho, ieee1588
        pmd_fwd_mode = '--forward-mode={} '.format(args['pmd_fwd_mode'])\
            if args.get('pmd_fwd_mode', '') else ''
        # Set the number of packets per burst to N.
        pmd_burst = '--burst=64 '
        # Set the number of descriptors in the TX rings to N.
        pmd_txd = '--txd=2048 '
        # Set the number of descriptors in the RX rings to N.
        pmd_rxd = '--rxd=2048 '
        # Set the hexadecimal bitmask of TX queue flags.
        pmd_txqflags = '--txqflags=0xf00 '
        # Set the number of mbufs to be allocated in the mbuf pools.
        pmd_total_num_mbufs = '--total-num-mbufs=65536 '
        # Set the hexadecimal bitmask of the ports for forwarding.
        pmd_portmask = '--portmask=0x3 '
        # Disable hardware VLAN.
        pmd_disable_hw_vlan = '--disable-hw-vlan '\
            if args.get('pmd_disable_hw_vlan', '') else ''
        # Disable RSS (Receive Side Scaling).
        pmd_disable_rss = '--disable-rss '\
            if args.get('pmd_disable_rss', '') else ''
        # Set the hexadecimal bitmask of the cores running forwarding. Master
        # lcore=0 is reserved, so highest bit is set to 0.
        pmd_coremask = '--coremask={} '.format(\
            hex(int(args['eal_coremask'], 0) & 0xFFFE))\
            if args.get('eal_coremask', '') else ''
        # Set the number of forwarding cores based on coremask.
        pmd_nb_cores = '--nb-cores={} '.format(\
            bin(int(args['eal_coremask'], 0) & 0xFFFE).count('1'))\
            if args.get('eal_coremask', '') else ''
        eal_options = '-v '\
            + eal_coremask\
            + eal_mem_channels\
            + eal_socket_mem\
            + eal_driver
        pmd_options = '-- '\
            + pmd_fwd_mode\
            + pmd_burst\
            + pmd_txd\
            + pmd_rxd\
            + pmd_txqflags\
            + pmd_total_num_mbufs\
            + pmd_portmask\
            + pmd_disable_hw_vlan\
            + pmd_disable_rss\
            + pmd_coremask\
            + pmd_nb_cores
        ssh = SSH()
        ssh.connect(node)
        cmd = "/start-testpmd.sh {0} {1}".format(eal_options, pmd_options)
        exec_cmd_no_error(node, cmd, sudo=True)
        ssh.disconnect(node)

    @staticmethod
    def dpdk_testpmd_stop(node):
        """Stop DPDK testpmd app on node.

        :param node: Node to stop testpmd on.
        :type node: dict
        :return: nothing
        """
        ssh = SSH()
        ssh.connect(node)
        cmd = "/stop-testpmd.sh"
        exec_cmd_no_error(node, cmd, sudo=True)
        ssh.disconnect(node)
