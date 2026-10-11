import json
import sys

from snakeoil2.dsp.params import PARAMS

json.dump(PARAMS.export(), sys.stdout, indent=2)
