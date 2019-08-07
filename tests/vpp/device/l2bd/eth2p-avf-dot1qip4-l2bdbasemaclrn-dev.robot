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

*** Settings ***
| Resource | resources/libraries/robot/shared/default.robot
| ...
| Force Tags | 2_NODE_SINGLE_LINK_TOPO | DEVICETEST | HW_ENV | DCR_ENV | SCAPY
| ... | NIC_Virtual | ETH | IP4FWD | BASE | DOT1Q | IP4BASE | DRV_AVF
| ...
| Suite Setup | Setup suite single link | avf | scapy
| Test Setup | Setup test
| Test Teardown | Tear down test | packet_trace
| ...
| Test Template | Local Template
| ...
| Documentation | *IPv4 routing with IEEE 802.1Q test cases*
| ...
| ... | *[Top] Network Topologies:* TG-DUT1-TG 2-node circular topology with\
| ... | single links between nodes.
| ... | *[Enc] Packet Encapsulations:* Eth-IPv4 for IPv4 routing. IEEE 802.1Q\
| ... | tagging is applied on links between TG-DUT1.
| ... | *[Cfg] DUT configuration:* DUT1 is configured with IPv4 routing and\
| ... | two static IPv4 /30 route entries. DUT1 is tested with ${nic_name}.
| ... | *[Ver] TG verification:* Test IPv4 packets are sent in one direction \
| ... | by TG on link to DUT1; on receive TG verifies packets for correctness \
| ... | and drops as applicable.
| ... | *[Ref] Applicable standard specifications:* IEEE 802.1q.

*** Variables ***
| @{plugins_to_enable}= | dpdk_plugin.so | avf_plugin.so
| ${nic_name}= | virtual
| ${overhead}= | ${4}

*** Keywords ***
| Local Template
| | [Documentation]
| | ... | [Ver] Make TG send ICMPv4 Echo Reqs in both directions between two\
| | ... | of its interfaces to be switched by DUT to and from docker; verify\
| | ... | all packets are received.
| | ...
| | ... | *Arguments:*
| | ... | - frame_size - Framesize in Bytes in integer. Type: integer
| | ... | - phy_cores - Number of physical cores. Type: integer
| | ... | - rxq - Number of RX queues, default value: ${None}. Type: integer
| | ...
| | [Arguments] | ${frame_size} | ${phy_cores} | ${rxq}=${None}
| | ...
| | Set Test Variable | \${frame_size}
| | ...
| | Given Add worker threads and rxqueues to all DUTs | ${phy_cores} | ${rxq}
| | And Add DPDK no PCI to all DUTs
| | And Set Max Rate And Jumbo
| | And Apply startup configuration on all VPP DUTs | with_trace=${True}
| | When Initialize AVF interfaces
| | And Initialize layer interface
| | And Initialize layer dot1q
| | And Initialize L2 bridge domain
| | Then Send ICMPv4 bidirectionally and verify received packets
| | ... | ${tg} | ${tg_if1} | ${tg_if2}

*** Test Cases ***
| tc01-68B-avf-dot1qip4-l2bdbasemaclrn-dev
| | [Tags] | 68B
| | frame_size=${68} | phy_cores=${0}