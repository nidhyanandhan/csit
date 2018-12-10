# Copyright (c) 2018 Cisco and/or its affiliates.
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
| Force Tags | 2_NODE_SINGLE_LINK_TOPO | PERFTEST | HW_ENV | MRR
| ... | NIC_Intel-XXV710 | ETH | IP4FWD | FEATURE | ACL | ACL_STATEFUL
| ... | IACL | ACL50 | 10k_FLOWS
| ...
| Suite Setup | Run Keywords
| ... | Set up 2-node performance topology with DUT's NIC model | L3
| ... | Intel-XXV710
| ... | AND | Set up performance test suite with ACL
| Suite Teardown | Tear down 2-node performance topology
| ...
| Test Setup | Set up performance test
| ...
| Test Teardown | Tear down performance mrr test
| ...
| Test Template | Local Template
| ...
| Documentation | *Raw results IPv4 test cases with ACL*
| ...
| ... | *[Top] Network Topologies:* TG-DUT1-TG 2-node circular topology\
| ... | with single links between nodes.
| ... | *[Enc] Packet Encapsulations:* Eth-IPv4-UDP for IPv4 routing.
| ... | *[Cfg] DUT configuration:* DUT1 is configured with IPv4 routing.\
| ... | Required ACL rules are applied to input paths of both DUT1 intefaces.\
| ... | DUT1 is tested with 2p25GE NIC XXV710 by Intel.
| ... | *[Ver] TG verification:* In MaxReceivedRate test TG sends traffic\
| ... | at line rate and reports total received/sent packets over trial period.\
| ... | Test packets are generated by TG on links to DUT1. TG traffic profile\
| ... | contains two L3 flow-groups (flow-group per direction, ${flows_per_dir}\
| ... | flows per flow-group) with all packets containing Ethernet header, IPv4\
| ... | header with IP protocol=61 and static payload. MAC addresses are\
| ... | matching MAC addresses of the TG node interfaces.
| ... | *[Ref] Applicable standard specifications:* RFC2544.

*** Variables ***
# XXV710-DA2 bandwidth limit ~49Gbps/2=24.5Gbps
| ${s_24.5G}= | ${24500000000}
# XXV710-DA2 Mpps limit 37.5Mpps/2=18.75Mpps
| ${s_18.75Mpps}= | ${18750000}

# ACL test setup
| ${acl_action}= | permit+reflect
| ${acl_apply_type}= | input
| ${no_hit_aces_number}= | 50
| ${flows_per_dir}= | 10k

# starting points for non-hitting ACLs
| ${src_ip_start}= | 30.30.30.1
| ${dst_ip_start}= | 40.40.40.1
| ${ip_step}= | ${1}
| ${sport_start}= | ${1000}
| ${dport_start}= | ${1000}
| ${port_step}= | ${1}
| ${trex_stream1_subnet}= | 10.10.10.0/24
| ${trex_stream2_subnet}= | 20.20.20.0/24

| ${traffic_profile}= | trex-sl-2n-ethip4udp-10u1000p-conc

*** Keywords ***
| Local Template
| | ...
| | [Documentation]
| | ... | [Cfg] DUT runs IPv4 routing config.
| | ... | Each DUT uses ${phy_cores} physical core(s) for worker threads.
| | ... | [Ver] Measure MaxReceivedRate for ${framesize}B frames using single\
| | ... | trial throughput test.
| | ...
| | ... | *Arguments:*
| | ... | - framesize - Framesize in Bytes in integer or string (IMIX_v4_1).
| | ... | Type: integer, string
| | ... | - phy_cores - Number of physical cores. Type: integer
| | ... | - rxq - Number of RX queues, default value: ${None}. Type: integer
| | ...
| | [Arguments] | ${framesize} | ${phy_cores} | ${rxq}=${None}
| | ...
| | Given Add worker threads and rxqueues to all DUTs | ${phy_cores} | ${rxq}
| | And Add PCI devices to all DUTs
| | ${max_rate} | ${jumbo} = | Get Max Rate And Jumbo And Handle Multi Seg
| | ... | ${s_24.5G} | ${framesize} | pps_limit=${s_18.75Mpps}
| | And Apply startup configuration on all VPP DUTs
| | ${ip_nr}= | Set Variable | 10
| | When Initialize IPv4 routing for '${ip_nr}' addresses with IPv4 ACLs on DUT1 in circular topology
| | Then Traffic should pass with maximum rate
| | ... | ${max_rate}pps | ${framesize} | ${traffic_profile}

*** Test Cases ***
| tc01-64B-1c-ethip4udp-ip4base-iacl50sf-10kflows-mrr
| | [Tags] | 64B | 1C
| | framesize=${64} | phy_cores=${1}

| tc02-64B-2c-ethip4udp-ip4base-iacl50sf-10kflows-mrr
| | [Tags] | 64B | 2C
| | framesize=${64} | phy_cores=${2}

| tc03-64B-4c-ethip4udp-ip4base-iacl50sf-10kflows-mrr
| | [Tags] | 64B | 4C
| | framesize=${64} | phy_cores=${4}

| tc04-1518B-1c-ethip4udp-ip4base-iacl50sf-10kflows-mrr
| | [Tags] | 1518B | 1C
| | framesize=${1518} | phy_cores=${1}

| tc05-1518B-2c-ethip4udp-ip4base-iacl50sf-10kflows-mrr
| | [Tags] | 1518B | 2C
| | framesize=${1518} | phy_cores=${2}

| tc06-1518B-4c-ethip4udp-ip4base-iacl50sf-10kflows-mrr
| | [Tags] | 1518B | 4C
| | framesize=${1518} | phy_cores=${4}

| tc07-9000B-1c-ethip4udp-ip4base-iacl50sf-10kflows-mrr
| | [Tags] | 9000B | 1C
| | framesize=${9000} | phy_cores=${1}

| tc08-9000B-2c-ethip4udp-ip4base-iacl50sf-10kflows-mrr
| | [Tags] | 9000B | 2C
| | framesize=${9000} | phy_cores=${2}

| tc09-9000B-4c-ethip4udp-ip4base-iacl50sf-10kflows-mrr
| | [Tags] | 9000B | 4C
| | framesize=${9000} | phy_cores=${4}

| tc10-IMIX-1c-ethip4udp-ip4base-iacl50sf-10kflows-mrr
| | [Tags] | IMIX | 1C
| | framesize=IMIX_v4_1 | phy_cores=${1}

| tc11-IMIX-2c-ethip4udp-ip4base-iacl50sf-10kflows-mrr
| | [Tags] | IMIX | 2C
| | framesize=IMIX_v4_1 | phy_cores=${2}

| tc12-IMIX-4c-ethip4udp-ip4base-iacl50sf-10kflows-mrr
| | [Tags] | IMIX | 4C
| | framesize=IMIX_v4_1 | phy_cores=${4}
