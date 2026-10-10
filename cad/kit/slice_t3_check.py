"""Check T3 with the bundled offline slicer, without sending a print job."""
import json
from slice_t4_check import ROOT,check

if __name__=='__main__':
    print(json.dumps(check(
        stl=ROOT/'cad/apex2-cage/print_now/T3_cage_section_socket_2_checked.stl',
        label='T3',expected_parts=10,layer_height='.15',solid_layers='5',max_height=5.49
    ),indent=2))
