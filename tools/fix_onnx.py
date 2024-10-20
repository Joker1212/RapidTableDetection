import onnx
from onnx import helper


def create_constant_tensor(name, value):
    tensor = helper.make_tensor(
        name=name, data_type=onnx.TensorProto.INT64, dims=[len(value)], vals=value
    )
    return tensor


# 创建新的 squeeze 节点
def create_squeeze_node(name, input_name, axes):
    const_tensor = create_constant_tensor(name + "_constant", axes)
    squeeze_node = helper.make_node(
        "Squeeze",
        inputs=[input_name, name + "_constant"],
        outputs=[input_name + "_squeezed"],
        name=name + "_Squeeze",
    )
    return const_tensor, squeeze_node


def fix_onnx(model_path):
    model = onnx.load(model_path)

    # 删除指定的节点
    deleted_nodes = ["p2o.Squeeze.3", "p2o.Squeeze.5"]
    nodes_to_delete = [node for node in model.graph.node if node.name in deleted_nodes]
    for node in nodes_to_delete:
        model.graph.node.remove(node)
    # 找到 gather8 和 gather10 的输出
    gather8_output = None
    gather10_output = None
    # 找到 'p2o.Gather.1' 节点
    for node in model.graph.node:
        if node.name == "p2o.Gather.0":
            gather_output_name = node.output[0]
            # break
        if node.name == "p2o.Gather.2":
            gather_output_name1 = node.output[0]
            # break

    for node in model.graph.node:
        if node.name == "p2o.Gather.8":
            node.input[0] = gather_output_name
            gather8_output = node.output[0]
        elif node.name == "p2o.Gather.10":
            node.input[0] = gather_output_name1
            gather10_output = node.output[0]

    if gather8_output:
        new_squeeze_components_8 = create_squeeze_node(
            "p2o.Gather.8", gather8_output, [1]
        )
        model.graph.initializer.append(new_squeeze_components_8[0])  # 添加常量张量
        model.graph.node.append(new_squeeze_components_8[1])  # 添加 Squeeze 节点

    if gather10_output:
        new_squeeze_components_10 = create_squeeze_node(
            "p2o.Gather.10", gather10_output, [1]
        )
        model.graph.initializer.append(new_squeeze_components_10[0])  # 添加常量张量
        model.graph.node.append(new_squeeze_components_10[1])  # 添加 Squeeze 节点

    # 更新依赖于 gather8 和 gather10 的节点输入
    for node in model.graph.node:
        if node.name == "p2o.Cast.0":
            node.input[0] = new_squeeze_components_8[1].output[0]

        if node.name == "p2o.Gather.12":
            node.input[1] = new_squeeze_components_10[1].output[0]

    # 保存修改后的模型
    onnx.save(model, model_path)
