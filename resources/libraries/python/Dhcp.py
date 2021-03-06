# Copyright (c) 2019 Cisco and/or its affiliates.
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

"""DHCP utilities for VPP."""


from resources.libraries.python.PapiExecutor import PapiSocketExecutor


class DhcpProxy:
    """DHCP Proxy utilities."""

    @staticmethod
    def vpp_get_dhcp_proxy(node, ip_version):
        """Retrieve DHCP relay configuration.

        :param node: VPP node.
        :param ip_version: IP protocol version: ipv4 or ipv6.
        :type node: dict
        :type ip_version: str
        :returns: DHCP relay data.
        :rtype: list
        """
        cmd = u"dhcp_proxy_dump"
        args = dict(is_ip6=1 if ip_version == u"ipv6" else 0)
        err_msg = f"Failed to get DHCP proxy dump on host {node[u'host']}"

        with PapiSocketExecutor(node) as papi_exec:
            details = papi_exec.add(cmd, **args).get_details(err_msg)

        return details
