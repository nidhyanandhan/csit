
.. raw:: latex

    \clearpage

.. raw:: html

    <script type="text/javascript">

        function getDocHeight(doc) {
            doc = doc || document;
            var body = doc.body, html = doc.documentElement;
            var height = Math.max( body.scrollHeight, body.offsetHeight,
                html.clientHeight, html.scrollHeight, html.offsetHeight );
            return height;
        }

        function setIframeHeight(id) {
            var ifrm = document.getElementById(id);
            var doc = ifrm.contentDocument? ifrm.contentDocument:
                ifrm.contentWindow.document;
            ifrm.style.visibility = 'hidden';
            ifrm.style.height = "10px"; // reset to minimal height ...
            // IE opt. for bing/msn needs a bit added or scrollbar appears
            ifrm.style.height = getDocHeight( doc ) + 4 + "px";
            ifrm.style.visibility = 'visible';
        }

    </script>

..
    ## 3n-hsw-xl710
    ### imix-ipsec-ip4routing-base-scale-sw-dpdk
    10ge2p1xl710-ethip4ipsec4tnlsw-ip4base-int-aes256gcm-ndrpdr
    10ge2p1xl710-ethip4ipsec4tnlsw-ip4base-int-aes128cbc-hmac512sha-ndrpdr
    10ge2p1xl710-ethip4ipsec1000tnlsw-ip4base-int-aes256gcm-ndrpdr
    10ge2p1xl710-ethip4ipsec1000tnlsw-ip4base-int-aes128cbc-hmac512sha-ndrpdr
    10ge2p1xl710-ethip4ipsec10000tnlsw-ip4base-int-aes256gcm-ndrpdr
    10ge2p1xl710-ethip4ipsec10000tnlsw-ip4base-int-aes128cbc-hmac512sha-ndrpdr

    ### imix-ipsec-ip4routing-base-scale-hw-dpdk
    10ge2p1xl710-ethip4ipsec1tnlhw-ip4base-int-aes256gcm-ndrpdr
    10ge2p1xl710-ethip4ipsec1tnlhw-ip4base-int-aes128cbc-hmac512sha-ndrpdr
    10ge2p1xl710-ethip4ipsec1000tnlhw-ip4base-int-aes256gcm-ndrpdr
    10ge2p1xl710-ethip4ipsec1000tnlhw-ip4base-int-aes128cbc-hmac512sha-ndrpdr

3n-hsw-xl710
~~~~~~~~~~~~

imix-ipsec-ip4routing-base-scale-sw-dpdk
----------------------------------------

.. raw:: html

    <center>
    <iframe id="01" onload="setIframeHeight(this.id)" width="700" frameborder="0" scrolling="no" src="../../_static/vpp/3n-hsw-xl710-imix-ipsec-ip4routing-base-scale-sw-dpdk-ndr-tsa.html"></iframe>
    <p><br></p>
    </center>

.. raw:: latex

    \begin{figure}[H]
        \centering
            \graphicspath{{../_build/_static/vpp/}}
            \includegraphics[clip, trim=0cm 0cm 5cm 0cm, width=0.70\textwidth]{3n-hsw-xl710-imix-ipsec-ip4routing-base-scale-sw-dpdk-ndr-tsa}
            \label{fig:3n-hsw-xl710-imix-ipsec-ip4routing-base-scale-sw-dpdk-ndr-tsa}
    \end{figure}

.. raw:: latex

    \clearpage

.. raw:: html

    <center>
    <iframe id="02" onload="setIframeHeight(this.id)" width="700" frameborder="0" scrolling="no" src="../../_static/vpp/3n-hsw-xl710-imix-ipsec-ip4routing-base-scale-sw-dpdk-pdr-tsa.html"></iframe>
    <p><br></p>
    </center>

.. raw:: latex

    \begin{figure}[H]
        \centering
            \graphicspath{{../_build/_static/vpp/}}
            \includegraphics[clip, trim=0cm 0cm 5cm 0cm, width=0.70\textwidth]{3n-hsw-xl710-imix-ipsec-ip4routing-base-scale-sw-dpdk-pdr-tsa}
            \label{fig:3n-hsw-xl710-imix-ipsec-ip4routing-base-scale-sw-dpdk-pdr-tsa}
    \end{figure}

.. raw:: latex

    \clearpage

imix-ipsec-ip4routing-base-scale-hw-dpdk
----------------------------------------

.. raw:: html

    <center>
    <iframe id="11" onload="setIframeHeight(this.id)" width="700" frameborder="0" scrolling="no" src="../../_static/vpp/3n-hsw-xl710-imix-ipsec-ip4routing-base-scale-hw-dpdk-ndr-tsa.html"></iframe>
    <p><br></p>
    </center>

.. raw:: latex

    \begin{figure}[H]
        \centering
            \graphicspath{{../_build/_static/vpp/}}
            \includegraphics[clip, trim=0cm 0cm 5cm 0cm, width=0.70\textwidth]{3n-hsw-xl710-imix-ipsec-ip4routing-base-scale-hw-dpdk-ndr-tsa}
            \label{fig:3n-hsw-xl710-imix-ipsec-ip4routing-base-scale-hw-dpdk-ndr-tsa}
    \end{figure}

.. raw:: latex

    \clearpage

.. raw:: html

    <center>
    <iframe id="12" onload="setIframeHeight(this.id)" width="700" frameborder="0" scrolling="no" src="../../_static/vpp/3n-hsw-xl710-imix-ipsec-ip4routing-base-scale-hw-dpdk-pdr-tsa.html"></iframe>
    <p><br></p>
    </center>

.. raw:: latex

    \begin{figure}[H]
        \centering
            \graphicspath{{../_build/_static/vpp/}}
            \includegraphics[clip, trim=0cm 0cm 5cm 0cm, width=0.70\textwidth]{3n-hsw-xl710-imix-ipsec-ip4routing-base-scale-hw-dpdk-pdr-tsa}
            \label{fig:3n-hsw-xl710-imix-ipsec-ip4routing-base-scale-hw-dpdk-pdr-tsa}
    \end{figure}
