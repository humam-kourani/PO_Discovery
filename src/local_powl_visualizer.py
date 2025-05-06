import base64
import os
import re
import importlib.resources
import tempfile
import webbrowser
from enum import Enum

import pm4py
from graphviz import Digraph
from pm4py.objects.process_tree.obj import Operator
from pm4py.util import exec_utils, constants
from typing import Optional, Dict, Any
from pm4py.objects.powl.obj import POWL, Transition, SilentTransition, StrictPartialOrder, OperatorPOWL, \
    FrequentTransition

OPERATOR_BOXES = True
FREQUENCY_TAG_IMAGES = True

min_width = "1.5"  # Set the minimum width in inches
min_height = "0.5"
fillcolor = "#fcfcfc"
opacity_change_ratio = 0.02


class Parameters(Enum):
    FORMAT = "format"
    COLOR_MAP = "color_map"
    ENABLE_DEEPCOPY = "enable_deepcopy"
    FONT_SIZE = "font_size"
    BGCOLOR = "bgcolor"
    ENABLE_GRAPH_TITLE = "enable_graph_title"
    GRAPH_TITLE = "graph_title"


def apply(powl: POWL, parameters: Optional[Dict[Any, Any]] = None) -> Digraph:
    """
    Obtain a POWL model representation through GraphViz

    Parameters
    -----------
    powl
        POWL model

    Returns
    -----------
    gviz
        GraphViz Digraph
    """
    if parameters is None:
        parameters = {}

    enable_graph_title = exec_utils.get_param_value(Parameters.ENABLE_GRAPH_TITLE, parameters, constants.DEFAULT_ENABLE_GRAPH_TITLES)
    graph_title = exec_utils.get_param_value(Parameters.GRAPH_TITLE, parameters, "POWL model")

    filename = tempfile.NamedTemporaryFile(suffix='.gv')

    viz = Digraph("powl", filename=filename.name, engine='dot')
    viz.attr('node', shape='ellipse', fixedsize='false')
    viz.attr(nodesep='1')
    viz.attr(ranksep='1')
    viz.attr(compound='true')
    viz.attr(overlap='scale')
    viz.attr(splines='true')
    viz.attr(rankdir='TB')
    viz.attr(style="filled")
    viz.attr(fillcolor=fillcolor)

    color_map = exec_utils.get_param_value(Parameters.COLOR_MAP, {}, {})

    repr_powl(powl, viz, color_map, level=0)
    viz.format = "svg"

    return viz


def get_color(node, color_map):
    """
    Gets a color for a node from the color map

    Parameters
    --------------
    node
        Node
    color_map
        Color map
    """
    if node in color_map:
        return color_map[node]
    return "black"


def get_id_base(powl):
    if isinstance(powl, Transition):
        return str(id(powl))
    if isinstance(powl, OperatorPOWL):
        # return str(id(powl))
        for node in powl.children:
            if not isinstance(node, SilentTransition):
                return get_id_base(node)
    if isinstance(powl, StrictPartialOrder):
        for node in powl.children:
            return get_id_base(node)



def get_id(powl):
    if isinstance(powl, Transition):
        return str(id(powl))
    if isinstance(powl, OperatorPOWL):
        if OPERATOR_BOXES:
            return "cluster_" + str(id(powl))
        else:
            return "clusterINVIS_" + str(id(powl))
    if isinstance(powl, StrictPartialOrder):
        return "cluster_" + str(id(powl))


def add_operator_edge(vis, current_node_id, child, directory='none', style=""):
    child_id = get_id(child)
    if child_id.startswith("cluster_"):
        vis.edge(current_node_id, get_id_base(child), dir=directory, lhead=child_id, style=style, minlen='2')
    else:
        vis.edge(current_node_id, get_id_base(child), dir=directory, style=style)


def add_order_edge(block, child_1, child_2, directory='forward', color="black", style=""):
    child_id_1 = get_id(child_1)
    child_id_2 = get_id(child_2)
    if child_id_1.startswith("cluster_"):
        if child_id_2.startswith("cluster_"):
            block.edge(get_id_base(child_1), get_id_base(child_2), dir=directory, color=color, style=style,
                       ltail=child_id_1, lhead=child_id_2, minlen='2')
        else:
            block.edge(get_id_base(child_1), get_id_base(child_2), dir=directory, color=color, style=style,
                       ltail=child_id_1, minlen='2')
    else:
        if child_id_2.startswith("cluster_"):
            block.edge(get_id_base(child_1), get_id_base(child_2), dir=directory, color=color, style=style,
                       lhead=child_id_2, minlen='2')
        else:
            block.edge(get_id_base(child_1), get_id_base(child_2), dir=directory, color=color, style=style)


def repr_powl(powl, viz, color_map, level, skip_order=False, block_id=None):
    font_size = "18"
    this_node_id = str(id(powl))

    current_color = darken_color(fillcolor, amount=opacity_change_ratio * level)

    if isinstance(powl, FrequentTransition):
        label = powl.activity
        if powl.skippable:
            if powl.selfloop:
                with importlib.resources.path("pm4py.visualization.powl.variants.icons", "skip-loop-tag.svg") as gimg:
                    image = str(gimg)
                    viz.node(this_node_id, label='\n' + label, imagepos='tr', image=image,
                             shape='box', width=min_width, fontsize=font_size, style='filled', fillcolor=current_color)
            else:
                with importlib.resources.path("pm4py.visualization.powl.variants.icons", "skip-tag.svg") as gimg:
                    image = str(gimg)
                    viz.node(this_node_id, label='\n' + label, imagepos='tr', image=image,
                             shape='box', width=min_width, fontsize=font_size, style='filled', fillcolor=current_color)
        else:
            if powl.selfloop:
                with importlib.resources.path("pm4py.visualization.powl.variants.icons", "loop-tag.svg") as gimg:
                    image = str(gimg)
                    viz.node(this_node_id, label='\n' + label, imagepos='tr', image=image,
                             shape='box', width=min_width, fontsize=font_size, style='filled', fillcolor=current_color)
            else:
                viz.node(this_node_id, label=label,
                         shape='box', width=min_width, fontsize=font_size, style='filled', fillcolor=current_color)
    elif isinstance(powl, Transition):
        if isinstance(powl, SilentTransition):
            viz.node(this_node_id, label='', style='filled', fillcolor='black', shape='square',
                     width='0.3', height='0.3', fixedsize="true")
        else:
            viz.node(this_node_id, str(powl.label), shape='box', fontsize=font_size, width=min_width, style='filled',
                     fillcolor=current_color)

    elif isinstance(powl, StrictPartialOrder):
        transitive_reduction = powl.order.get_transitive_reduction()
        if not block_id:
            block_id = get_id(powl)
        with viz.subgraph(name=block_id) as block:
            block.attr(margin="20,20")
            block.attr(style="filled")
            block.attr(label="")
            block.attr(fillcolor=current_color)
            if skip_order:
                with importlib.resources.path("pm4py.visualization.powl.variants.icons", "skip-tag.svg") as gimg:
                    image = str(gimg)
                    block.attr(label=f'''<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">
                                            <TR><TD WIDTH="55" HEIGHT="27" FIXEDSIZE="TRUE"><IMG SRC="{image}" SCALE="BOTH"/></TD></TR>
                                            </TABLE>>''')
                    block.attr(labeljust='r')
            else:
                block.attr(label="")

            for child in powl.children:
                repr_powl(child, block, color_map, level=level + 1)
            for child in powl.children:
                for child2 in powl.children:
                    if transitive_reduction.is_edge(child, child2):
                        add_order_edge(block, child, child2)

    elif isinstance(powl, OperatorPOWL):
        block_id = get_id(powl)
        if powl.operator == Operator.XOR and len(powl.children) == 2:
            child_0 = powl.children[0]
            child_1 = powl.children[1]
            if isinstance(child_0, SilentTransition) and isinstance(child_1, StrictPartialOrder):
                repr_powl(child_1, viz, color_map, level=level, skip_order=True, block_id=block_id)
                return
            if isinstance(child_1, SilentTransition) and isinstance(child_0, StrictPartialOrder):
                repr_powl(child_0, viz, color_map, level=level, skip_order=True, block_id=block_id)
                return

        with viz.subgraph(name=block_id) as block:
            block.attr(label="")
            block.attr(margin="20,20")
            block.attr(style="filled")
            block.attr(fillcolor=current_color)
            if powl.operator == Operator.LOOP:
                with importlib.resources.path("pm4py.visualization.powl.variants.icons", "loop.svg") as gimg:
                    image = str(gimg)
                    block.node(this_node_id, image=image, label="", fontsize=font_size,
                               width='0.4', height='0.4', fixedsize="true")
                do = powl.children[0]
                redo = powl.children[1]
                repr_powl(do, block, color_map, level=level + 1)
                add_operator_edge(block, this_node_id, do)
                repr_powl(redo, block, color_map, level=level + 1)
                add_operator_edge(block, this_node_id, redo, style="dashed")
            elif powl.operator == Operator.XOR:
                with importlib.resources.path("pm4py.visualization.powl.variants.icons", "xor.svg") as gimg:
                    image = str(gimg)
                    block.node(this_node_id, image=image, label="", fontsize=font_size,
                               width='0.4', height='0.4', fixedsize="true")
                for child in powl.children:
                    repr_powl(child, block, color_map, level=level + 1)
                    add_operator_edge(block, this_node_id, child)


def darken_color(color, amount):
    """ Darkens the given color by the specified amount """
    import matplotlib.colors as mcolors
    amount = min(0.3, amount)

    rgb = mcolors.to_rgb(color)
    darker = [x * (1 - amount) for x in rgb]
    return mcolors.to_hex(darker)


def view(powl: POWL):
    powl = powl.simplify_using_frequent_transitions()
    gviz = apply(powl)
    svg_content = gviz.pipe().decode('utf-8')
    svg_content_with_inline_images = inline_images_and_svgs(svg_content)
    with tempfile.NamedTemporaryFile(delete=False, mode='w+', suffix='.svg') as tmpfile:
        tmpfile.write(svg_content_with_inline_images)
        tmpfile_path = tmpfile.name

        absolute_path = os.path.abspath(tmpfile_path)
        return webbrowser.open('file://' + absolute_path)

def inline_images_and_svgs(svg_content):
    img_pattern = re.compile(r'<image[^>]+xlink:href=["\'](.*?)["\'][^>]*>')

    def encode_file_to_base64(file_path):
        with open(file_path, 'rb') as file:
            return base64.b64encode(file.read()).decode('utf-8')

    def read_file_content_and_viewbox(file_path):
        with open(file_path, 'r') as file:
            content = file.read()
            content = re.sub(r'<\?xml.*?\?>', '', content, flags=re.DOTALL)
            content = re.sub(r'<!DOCTYPE.*?>', '', content, flags=re.DOTALL)
            viewBox_match = re.search(r'viewBox="([^"]*)"', content)
            viewBox = viewBox_match.group(1) if viewBox_match else "0 0 1 1"
            svg_content_match = re.search(r'<svg[^>]*>(.*?)</svg>', content, re.DOTALL)
            svg_content = svg_content_match.group(1) if svg_content_match else content
            return svg_content, viewBox

    def replace_with_inline_content(match):
        file_path = match.group(1)
        if file_path.lower().endswith('.svg'):
            svg_data, viewBox = read_file_content_and_viewbox(file_path)
            viewBox_values = [float(v) for v in viewBox.split()]
            actual_width, actual_height = viewBox_values[2], viewBox_values[3]

            intended_width = float(match.group(0).split('width="')[1].split('"')[0].replace('px', ''))
            intended_height = float(match.group(0).split('height="')[1].split('"')[0].replace('px', ''))
            x = float(match.group(0).split('x="')[1].split('"')[0])
            y = float(match.group(0).split('y="')[1].split('"')[0])

            scale_x = intended_width / actual_width
            scale_y = intended_height / actual_height

            return f'<g transform="translate({x},{y}) scale({scale_x},{scale_y})">{svg_data}</g>'
        else:
            base64_data = encode_file_to_base64(file_path)
            return match.group(0).replace(file_path, f"data:image/png;base64,{base64_data}")

    return img_pattern.sub(replace_with_inline_content, svg_content)
