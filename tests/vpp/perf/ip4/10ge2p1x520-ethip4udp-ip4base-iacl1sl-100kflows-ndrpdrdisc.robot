# Copyright (c) 2017 Cisco and/or its affiliates.
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
| Resource | resources/libraries/robot/performance/performance_setup.robot
| ...
| Force Tags | 3_NODE_SINGLE_LINK_TOPO | PERFTEST | HW_ENV | NDRPDRDISC
| ... | NIC_Intel-X520-DA2 | ETH | IP4FWD | FEATURE | ACL | ACL_STATELESS
| ... | IACL | ACL1 | 100k_FLOWS
| ...
| Suite Setup | Set up 3-node performance topology with DUT's NIC model
| ... | L3 | Intel-X520-DA2
| Suite Teardown | Tear down 3-node performance topology
| ...
| Test Setup | Set up performance test
| ...
| Test Teardown | Tear down performance test with ACL
| ... | ${min_rate}pps | ${framesize} | ${traffic_profile}
| ...
| Documentation | *RFC2544: Packet throughput IPv4 test cases with ACL*
| ...
| ... | *[Top] Network Topologies:* TG-DUT1-DUT2-TG 3-node circular topology\
| ... | with single links between nodes.
| ... | *[Enc] Packet Encapsulations:* Eth-IPv4-UDP for L2 switching of IPv4.
| ... | *[Cfg] DUT configuration:* DUT1 is configured with L2 bridge domain\
| ... | and MAC learning enabled. DUT2 is configured with L2 cross-connects.\
| ... | Required ACL rules are applied to input paths of both DUT1 intefaces.\
| ... | DUT1 and DUT2 are tested with 2p10GE NIC X520 Niantic by Intel.\
| ... | *[Ver] TG verification:* TG finds and reports throughput NDR (Non Drop\
| ... | Rate) with zero packet loss tolerance or throughput PDR (Partial Drop\
| ... | Rate) with non-zero packet loss tolerance (LT) expressed in percentage\
| ... | of packets transmitted. NDR and PDR are discovered for different\
| ... | Ethernet L2 frame sizes using either binary search or linear search\
| ... | algorithms with configured starting rate and final step that determines\
| ... | throughput measurement resolution. Test packets are generated by TG on\
| ... | links to DUTs. TG traffic profile contains two L3 flow-groups\
| ... | (flow-group per direction, ${flows_per_dir} flows per flow-group) with\
| ... | all packets containing Ethernet header, IPv4 header with UDP header and\
| ... | static payload. MAC addresses are matching MAC addresses of the TG node\
| ... | interfaces.
| ... | *[Ref] Applicable standard specifications:* RFC2544.

*** Variables ***
# X520-DA2 bandwidth limit
| ${s_limit}= | ${10000000000}

# ACL test setup
| ${acl_action}= | permit
| ${acl_apply_type}= | input
| ${no_hit_aces_number}= | 1
| ${flows_per_dir}= | 100k

# starting points for non-hitting ACLs
| ${src_ip_start}= | 30.30.30.1
| ${dst_ip_start}= | 40.40.40.1
| ${ip_step}= | ${1}
| ${sport_start}= | ${1000}
| ${dport_start}= | ${1000}
| ${port_step}= | ${1}
| ${trex_stream1_subnet}= | 10.10.10.0/24
| ${trex_stream2_subnet}= | 20.20.20.0/24

*** Keywords ***
| Discover NDR or PDR for IPv4 routing with ACLs
| | [Arguments] | ${wt} | ${rxq} | ${framesize} | ${min_rate} | ${search_type}
| | Set Test Variable | ${framesize}
| | Set Test Variable | ${min_rate}
| | ${max_rate}= | Calculate pps | ${s_limit} | ${framesize}
| | ${binary_min}= | Set Variable | ${min_rate}
| | ${binary_max}= | Set Variable | ${max_rate}
| | ${threshold}= | Set Variable | ${min_rate}
| | Given Add '${wt}' worker threads and '${rxq}' rxqueues in 3-node single-link circular topology
| | And Add PCI devices to DUTs in 3-node single link topology
| | ${get_framesize}= | Get Frame Size | ${framesize}
| | And Run Keyword If | ${get_framesize} < ${1522} | Add no multi seg to all DUTs
| | And Apply startup configuration on all VPP DUTs
| | ${ip_nr}= | Set Variable | 100
| | When Initialize IPv4 routing for '${ip_nr}' addresses with IPv4 ACLs on DUT1 in 3-node circular topology
| | ${traffic_profile}= | Set Variable | trex-sl-3n-ethip4udp-100u1000p-conc
| | Set Test Variable | ${traffic_profile}
| | Then Run Keyword If | '${search_type}' == 'NDR'
| | ... | Find NDR using binary search and pps
| | ... | ${framesize} | ${binary_min} | ${binary_max} | ${traffic_profile}
| | ... | ${min_rate} | ${max_rate} | ${threshold}
| | ... | ELSE IF | '${search_type}' == 'PDR'
| | ... | Find PDR using binary search and pps
| | ... | ${framesize} | ${binary_min} | ${binary_max} | ${traffic_profile}
| | ... | ${min_rate} | ${max_rate} | ${threshold}
| | ... | ${perf_pdr_loss_acceptance} | ${perf_pdr_loss_acceptance_type}

*** Test Cases ***
| tc01-64B-1t1c-ethip4udp-ip4base-iacl1-stateless-flows100k-ndrdisc
| | [Documentation]
| | ... | [Cfg] DUT runs IPv4 routing config with ACL with\
| | ... | 1 thread, 1 phy core, 1 receive queue per NIC port.
| | ... | [Ver] Find NDR for 64 Byte frames using binary search start at 10GE\
| | ... | linerate, step 10kpps.
| | ...
| | [Tags] | 64B | 1T1C | STHREAD | NDRDISC
| | ...
| | [Template] | Discover NDR or PDR for IPv4 routing with ACLs
| | wt=1 | rxq=1 | framesize=${64} | min_rate=${10000} | search_type=NDR

| tc02-64B-1t1c-ethip4udp-ip4base-iacl1-stateless-flows100k-pdrdisc
| | [Documentation]
| | ... | [Cfg] DUT runs IPv4 routing config with ACL with\
| | ... | 1 thread, 1 phy core, 1 receive queue per NIC port.
| | ... | [Ver] Find PDR for 64 Byte frames using binary search start at 10GE\
| | ... | linerate, step 10kpps, LT=0.5%.
| | ...
| | [Tags] | 64B | 1T1C | STHREAD | PDRDISC | SKIP_PATCH
| | ...
| | [Template] | Discover NDR or PDR for IPv4 routing with ACLs
| | wt=1 | rxq=1 | framesize=${64} | min_rate=${10000} | search_type=PDR

| tc03-64B-2t2c-ethip4udp-ip4base-iacl1-stateless-flows100k-ndrdisc
| | [Documentation]
| | ... | [Cfg] DUT runs IPv4 routing config with ACL with\
| | ... | 2 threads, 2 phy cores, 1 receive queue per NIC port.
| | ... | [Ver] Find NDR for 64 Byte frames using binary search start at 10GE\
| | ... | linerate, step 10kpps.
| | ...
| | [Tags] | 64B | 2T2C | MTHREAD | NDRDISC
| | ...
| | [Template] | Discover NDR or PDR for IPv4 routing with ACLs
| | wt=2 | rxq=1 | framesize=${64} | min_rate=${10000} | search_type=NDR

| tc04-64B-2t2c-ethip4udp-ip4base-iacl1-stateless-flows100k-pdrdisc
| | [Documentation]
| | ... | [Cfg] DUT runs IPv4 routing config with ACL with\
| | ... | 2 threads, 2 phy cores, 1 receive queue per NIC port.
| | ... | [Ver] Find PDR for 64 Byte frames using binary search start at 10GE\
| | ... | linerate, step 10kpps, LT=0.5%.
| | ...
| | [Tags] | 64B | 2T2C | MTHREAD | PDRDISC | SKIP_PATCH
| | ...
| | [Template] | Discover NDR or PDR for IPv4 routing with ACLs
| | wt=2 | rxq=1 | framesize=${64} | min_rate=${10000} | search_type=PDR
