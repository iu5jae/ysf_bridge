# ysf_bridge

The software requires Python version 3 and allows the connection between the following systems operating in C4FM with YSF protocol:

a) YSF reflector <> YSF Reflector<br>
b) YSF reflector <> YCS server<br>
c) YSF reflector <> XLX reflector<br>
d) YSF reflector <> master BrandMeister (YSF Direct mode)<br>
... and related combinations.<br>

The use of pYSF reflector is recommended if there is no need to manage multiple flows, otherwise pYSF3. Below are the links to the respective software:<br>
https://github.com/iu5jae/pYSFReflector<br>
https://github.com/iu5jae/pYSFReflector3

ysf_bridge is recommended to run from /opt/ysf_bridge2 directory and is managed by the ysf_bridge.ini file<br>
Check the log path.<br>
If you want to activate multiple bridges, you need to run multiple instances of ysf_bridge, each with its own configuration file and taking care to keep the streams separate from each other.<br>
A Callsign-nn can be indicated (to manage fixed connections between systems, e.g. pYSF3) where nn = DGID in use or by enabling ycs_connection = 1 specify the fixed DGID ycs_ID = nn<br>
Address and port must be specified for each endpoint of the systems to be connected together, while the Direct mode connection is for endpoint A only and is used to directly connect the BM master, with the same password as that entered in the BM/hotspot self care.<br> In Direct mode the TalkGroup to use (DMR side) is specified in options=group=22251 for example and the authentication DMR ID in ysfgateway_ID.

To run ysf_bridge the syntax is:
/opt/ysf_bridge2/ysf_bridge.py /opt/ysf_bridge2/ysf_bridge.ini<br>
check the correct path, also in the . service if this execution mode is used.<br>

Please note: this experimental software is for amateur radio use only, no guarantee of good operation is assumed, and no form of support is given. Respect the rules that system administrators indicate and do not make connections between networks or systems without having given prior information and received approval. Respect for each other and for what is in place is fundamental.
