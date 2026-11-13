"""Print ONNX nodes directly reading the recurrent state and their slice bounds."""
import sys
import onnx
from onnx import numpy_helper

model = onnx.load(sys.argv[1], load_external_data=False)
producers = {out: node for node in model.graph.node for out in node.output}
initializers = {x.name: numpy_helper.to_array(x) for x in model.graph.initializer}

def value(name):
    if name in initializers:
        return initializers[name].tolist()
    node = producers.get(name)
    if node and node.op_type == "Constant":
        for attr in node.attribute:
            if attr.name == "value":
                return numpy_helper.to_array(attr.t).tolist()
    return "?"

for node in model.graph.node:
    if any(x in node.input for x in
           ("state", "core_state", "roll_state", "/Reshape_output_0", "/Reshape_1_output_0",
            "/Split_output_0", "/Split_output_1", "/Split_output_2",
            "/Split_output_3", "/Split_output_4")):
        print(node.op_type, "inputs", list(node.input),
              "parameters", [value(x) for x in node.input[1:]],
              "attributes", [(a.name, list(a.ints)) for a in node.attribute if a.ints],
              "output", list(node.output))
