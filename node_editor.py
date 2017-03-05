#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import sys
import math
import json
import copy
import weakref
import logging as log
from path import Path
from PySide import QtCore, QtGui
from collections import defaultdict
from functools import partial

log.basicConfig(level=log.DEBUG, format="%(levelname)s from '%(module)s' : %(message)s")

MODULE_FOLDER = os.path.dirname(__file__)
NODE_TYPES_FOLDER = os.path.join(MODULE_FOLDER, "nodes")
ENUMS_INFO = json.load(open(os.path.join(NODE_TYPES_FOLDER, "enums.info")))
ICON_PATH = os.path.join(MODULE_FOLDER, "icons", "MDL Editor Icon.png")
IMAGE_EXTENSION = ".png"

import modules.parameter_editor as pe
reload(pe)

# TODO's:
    # Add regex check for parameter inputs
    # Break connections for published parameters
    # Preview connections (during connection creation)
    # Implement custom 'get_struct_component' node
    # Only those slot input values, that differ from default values should go into the final mdl code
    # Parameter editor should show the names of published attributes
    # Show uniform/varying info as slot's hint 
    # Plus/Minus/Multiply, Divide Nodes
    # Reset zoom to 100% function
    # Create node icons
    # Render preview?
    # Color as input for the normal map
    # Do not create new connection if input slot already has one

# LIMITATION's
    # Node with array inputs are not supported
    # Currently it is not allowed to create nodes
    # with names that are not file system conform (like *, +, etc.)
    # Every mdl file contains only one material with the name identical to file name

def replace_indentated_text(text_as_list_of_lines, 
    replacement_maker, replacement_content):
    """
    'replacement_maker' will be replaced with 'replacement_content'.
    'replacement_content' is as 'text_as_list_of_lines' also a list if lines.
    """

    result = []
    for line in text_as_list_of_lines[:]:
        if replacement_maker in line:

            if len(replacement_content)==0:

                result.append(line.replace(replacement_maker, "").replace(replacement_maker+"\n", ""))
                continue

            elif len(replacement_content)==1:

                result.append(line.replace(replacement_maker, replacement_content[0]))
                continue

            else:

                marker_position = line.index(replacement_maker)
                first_part = line.split(replacement_maker)[0]
                second_part = line.split(replacement_maker)[1]
                for i, rline in enumerate(replacement_content):
                    if i==0:
                        result.append(first_part+rline)
                    elif i==(len(replacement_content)-1):
                        result.append(" "*marker_position+rline+second_part)
                    else:
                        result.append(" "*marker_position+rline)
        else:
            result.append(line)

    return result

def scan_available_nodes(source_path):

    nodes_info = {}

    nodes = defaultdict(list)

    description_files = Path(source_path).walkfiles("*.description")
    content_files = Path(source_path).walkfiles("*.content")

    for description_file in description_files:
        nodes[description_file.namebase].append(description_file)

    for content_file in content_files:
        nodes[content_file.namebase].append(content_file)

    for node_type, node_files in nodes.items():
        if len(node_files)==2:
            description_file = node_files[0]
            content_file = node_files[1]
            with open(description_file) as f:
                description = json.load(f)

            with open(content_file) as f:
                content = f.readlines()
            nodes_info[node_type] = {"description" : description, "content" : content}

    return nodes_info

class SlotItem(QtGui.QGraphicsItem, QtCore.QObject):

    connection_request = QtCore.Signal(QtGui.QGraphicsItem, QtGui.QGraphicsItem)

    def __init__(self, name, slot_radius=None, is_parameter=False, has_default_value=True):

        QtCore.QObject.__init__(self)
        QtGui.QGraphicsItem.__init__(self)
        self.name = name
        self.is_parameter = is_parameter
        self.has_default_value = has_default_value
        self.radius = 4 if not slot_radius else slot_radius
        self.default_color = QtCore.Qt.darkGreen if self.is_parameter else QtCore.Qt.green
        self.color = self.default_color
        self.setAcceptDrops(True)

    def boundingRect(self):

        return QtCore.QRectF(-self.radius, -self.radius, 2*self.radius, 2*self.radius)

    def paint(self, painter, style, widget):

        b = QtGui.QBrush(self.color)
        painter.setBrush(b)

        p = painter.pen()
        p.setWidth(1)
            # p.setColor(QtGui.QColor(QtCore.Qt.black))
        # else:
        if not self.has_default_value:
            # p.setWidth()
            p.setStyle(QtCore.Qt.DashLine)
            # p.setColor(QtGui.QColor(0, 0, 0, 0))
        painter.setPen(p)

        r = self.radius # + (0 if self.has_default_value else 2)
        painter.drawEllipse(-r, -r, 2*r, 2*r)

    def dropEvent(self, event):

        self.connection_request.emit(event.mimeData().source_slot, self)

    def mousePressEvent(self, event):
        
        super(SlotItem, self).mousePressEvent(event)
        if event.button() == QtCore.Qt.LeftButton:
            drag = QtGui.QDrag(event.widget())
            mime = QtCore.QMimeData()
            mime.source_slot = self
            drag.setMimeData(mime)
            drop_action = drag.exec_()

            # self.setCursor(QtCore.Qt.OpenHandCursor)
            # self.setCursor(QtCore.Qt.ClosedHandCursor)
            # self.setCursor(QtCore.Qt.ArrowCursor)

    def publish(self, published_name):

        # self.color = QtCore.Qt.white
        self.setToolTip("Published as: " + published_name)
        self.color = QtGui.QColor(230, 255, 230)

    def unpublish(self):
        
        self.setToolTip(None)
        self.color = self.default_color
        
class NodeItem(QtGui.QGraphicsItem, QtCore.QObject):

    overload_changed = QtCore.Signal(QtGui.QGraphicsItem)

    def __init__(self, node_type, node_info):

        QtGui.QGraphicsItem.__init__(self)
        QtCore.QObject.__init__(self)

        # Visual attributes
        self.base_width = 74
        self.base_heigth = 120
        self.slot_radius = 5
        self.corner_radius = 5
        self.text_offset = 3
        self.icon_size = 64
        self.base_color = (220, 215, 220, 192)

        # Logical attributes
        self.node_type = node_type
        self.node_info = copy.deepcopy(node_info)
        self.input_slots = {} # "slot_name" : (slot_info, slot_object)
        self.output_slots = {} # "slot_name" : (slot_info, slot_object)
        self.connections = defaultdict(weakref.WeakSet) # slot_object : connection_object
        self.overload_buttons = []
        first_overload = self.node_info["description"]["overloads"][0]
        self.current_overload = first_overload["name"]
        self.description = first_overload

        # Widget flags
        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable)
        self.setFlag(QtGui.QGraphicsItem.ItemSendsGeometryChanges)
        self.setZValue(0)

        self.create_icon()
        self.create_overload_buttons()
        self.load_overload_info()

    def create_icon(self):

        icon_path = os.path.join(NODE_TYPES_FOLDER, self.node_type + IMAGE_EXTENSION)
        if not os.path.exists(icon_path):
            close_icon = QtGui.QApplication.instance().style().standardIcon(QtGui.QStyle.SP_TitleBarCloseButton)
            pixmap = close_icon.pixmap(self.icon_size, self.icon_size).scaled(self.icon_size, self.icon_size)
        else:
            pixmap = QtGui.QPixmap(icon_path).scaled(self.icon_size, self.icon_size)

        pixmap_item = QtGui.QGraphicsPixmapItem(pixmap)

        pixmap_item.setParentItem(self)
        pixmap_item.setPos((self.base_width-self.icon_size)/2.0, 2*self.text_offset)        

    def create_overload_buttons(self):

        def set_current_overload(event, overload_name):

            if event.button()==QtCore.Qt.MiddleButton:
                self.current_overload = overload_name
                self.load_overload_info()
                event.accept()
        
        SIZE = 10

        max_hor_count = self.base_width/(SIZE + self.text_offset)

        if len(self.node_info["description"]["overloads"])>1:
        
            for i, overload_info in enumerate(self.node_info["description"]["overloads"]):
                overload_button = QtGui.QGraphicsRectItem(0, 0, SIZE, SIZE)
                overload_button.setBrush(QtGui.QColor(150, 200, 140))
                overload_button.setPen(QtGui.QColor(150, 200, 140))
                overload_button.setToolTip(overload_info["name"])
                overload_button.setParentItem(self)
                overload_button.overload_name = overload_info["name"]
                # It looks like dirty hack, but it works
                overload_button.mousePressEvent = partial(set_current_overload, overload_name=overload_button.overload_name)
                x_position = 2*self.text_offset + (i%max_hor_count)*(SIZE + self.text_offset)
                y_position = 4*self.text_offset + self.icon_size + i/(max_hor_count)*(SIZE + self.text_offset)
                overload_button.setPos(x_position, y_position)
                self.overload_buttons.append(overload_button)

            overload_buttons_height = (len(self.overload_buttons)/max_hor_count-1)*((SIZE + self.text_offset))
            self.base_heigth = self.base_heigth + overload_buttons_height

    def clear_node(self):

        def remove_child_widgets(item):

            for child in item.childItems():
                remove_child_widgets(child)
                if not isinstance(child, (QtGui.QGraphicsRectItem, QtGui.QGraphicsProxyWidget, QtGui.QGraphicsPixmapItem)):
                    child.setParentItem(None)

        deleted_connectons = {"inputs" : {}, "outputs" : {}} # inputs/outputs : {source_slot_name : destination_slot_object}
                    
        # Break existing connections, but save the info about them
        for slot, connections in self.connections.items():
            for connection in connections:
                if connection.target_slot.name in self.input_slots:
                    deleted_connectons["inputs"][connection.target_slot.name] = connection.source_slot
                elif connection.source_slot.name in self.output_slots:
                    deleted_connectons["outputs"][connection.source_slot.name] = connection.target_slot
                connection.delete_it()
        self.connections.clear()

        # Clear input slot dictionaries
        for slot_object in [el[1] for el in self.input_slots.values()]:
            if slot_object:
                slot_object.setParentItem(None)
        self.input_slots.clear()

        # Clear output slot dictionaries
        for slot_object in [el[1] for el in self.output_slots.values()]:
            slot_object.setParentItem(None)
        self.output_slots.clear()

        remove_child_widgets(self)
        return deleted_connectons

    def load_overload_info(self):

        BUTTON_COLOR = 150, 200, 140

        def generate_node_name_label(node_type):

            node_name_label = QtGui.QGraphicsSimpleTextItem(node_type.upper())
            label_font = node_name_label.font()
            label_font.setWeight(QtGui.QFont.Black)
            node_name_label.setFont(label_font)
            return node_name_label

        def generate_hor_gradient():

            rect = QtGui.QGraphicsRectItem(0, -self.slot_radius*1.25, self.base_width*0.8, 2.5*self.slot_radius)
            gradient = QtGui.QLinearGradient(0, 0, self.base_width*0.8, 3*self.slot_radius)
            gradient.setSpread(QtGui.QGradient.PadSpread)
            gradient.setColorAt(0.0, QtGui.QColor(240, 250, 240, 230))
            gradient.setColorAt(1.0, QtGui.QColor(220, 230, 220, 0))
            brush = QtGui.QBrush(gradient)
            pen = QtGui.QPen(QtGui.QColor(0, 0, 0, 0))
            rect.setBrush(brush) 
            rect.setPen(pen) 
            rect.setFlags(QtGui.QGraphicsItem.ItemStacksBehindParent)
            return rect

        deleted_connectons = self.clear_node()
    
        # Change button's color
        for button in self.overload_buttons:
            if button.overload_name == self.current_overload:
                button.setBrush(QtGui.QColor(BUTTON_COLOR[0], BUTTON_COLOR[1], BUTTON_COLOR[2]))
            else:
                button.setBrush(QtGui.QColor(BUTTON_COLOR[0], BUTTON_COLOR[1], BUTTON_COLOR[2], 50))

        # Find correct overload info
        for overload_info in self.node_info["description"]["overloads"]:
            if overload_info["name"] == self.current_overload:
                self.description = overload_info 
                break

        # Create node name and set it's position
        node_name_label = generate_node_name_label(self.node_type)
        node_name_label.setParentItem(self)            
        node_name_label.setPos((self.base_width - node_name_label.boundingRect().width())/2.0, -self.text_offset-node_name_label.boundingRect().height()-self.text_offset)

        # Get slots names
        # input_slot_names = [item["name"] for item in self.description["inputs"] if item["expose_as_input"]]
        input_slot_names = [item["name"] for item in self.description["inputs"]]
        output_slot_names = [item["name"] for item in self.description["outputs"]]


        # Create input slot items and populate input slots dictionary
        for i, slot_name in enumerate(input_slot_names):
            slot_info = [d for d in self.description["inputs"] if d["name"] == slot_name][0]
            slot_type = slot_info["type"]
            has_default_value = slot_info.get("spec_default_value") is not None
            is_parameter = slot_info.get("expose_as_parameter")

            if slot_info["expose_as_input"]:

                slot_name_label = QtGui.QGraphicsSimpleTextItem("{n} ({t})".format(n=slot_name, t=slot_type))
                slot_name_label.setParentItem(self)
                slot_x_position = -self.slot_radius-self.text_offset-slot_name_label.boundingRect().width()
                slot_y_position = self.base_heigth + i*4*self.slot_radius - (slot_name_label.boundingRect().height()/2.0)
                slot_name_label.setPos(slot_x_position, slot_y_position)

                slot_item = SlotItem(slot_name, self.slot_radius, is_parameter=is_parameter, has_default_value=has_default_value)
                slot_item.setParentItem(self)
                slot_item.setPos(0, self.base_heigth + i*4*self.slot_radius)
                slot_item.type = slot_type

                rect = generate_hor_gradient()
                rect.setParentItem(slot_item)
            else:
                slot_item = None

            # Initialize the values of exposed as parameters inputs
            if slot_info["expose_as_parameter"]:
                slot_info.update({"value" : copy.deepcopy(slot_info["default_value"])})

            self.input_slots[slot_name] = slot_info, slot_item

        # Create output slot items and populate output slots dictionary
        for i, slot_name in enumerate(output_slot_names):

            slot_info = [d for d in self.description["outputs"] if d["name"] == slot_name][0]
            slot_type = slot_info["type"]
            slot_name_label = QtGui.QGraphicsSimpleTextItem("{n} ({t})".format(n=slot_name, t=slot_type))
            slot_name_label.setParentItem(self)
            slot_name_label.setPos(self.base_width + self.slot_radius + self.text_offset, self.base_heigth + i*4*self.slot_radius - (slot_name_label.boundingRect().height()/2.0))

            slot_item = SlotItem(slot_name, self.slot_radius)
            slot_item.setParentItem(self)
            slot_item.setPos(self.base_width, self.base_heigth + i*4*self.slot_radius)

            slot_item.type = slot_type

            self.output_slots[slot_name] = slot_info, slot_item

        # Recreate input connections if possible
        for target_slot_name, source_slot in deleted_connectons["inputs"].items():
            if target_slot_name in self.input_slots:
                for view in self.scene().views():
                    target_slot = self.input_slots[target_slot_name][1]
                    if target_slot:
                        view.add_connection(source_slot, self.input_slots[target_slot_name][1])

        # Recreate output connections if possible
        for source_slot_name, target_slot in deleted_connectons["outputs"].items():
            if source_slot_name in self.output_slots:
                for view in self.scene().views():
                    view.add_connection(self.output_slots[source_slot_name][1], target_slot)

        if self.scene():
            self.scene().update()

        # Update bounding box parameters
        max_slots_count = max([len(input_slot_names), len(output_slot_names)])
        self.full_width = self.base_width + 2*self.slot_radius
        self.full_heigth = self.base_heigth + 4*self.slot_radius*max_slots_count

        self.overload_changed.emit(self)

    def boundingRect(self):

        self.bb = QtCore.QRectF(-self.slot_radius, 0, self.full_width, self.full_heigth)
        return self.bb

    def paint(self, painter, style, widget):

        painter.setBrush(QtGui.QColor(*self.base_color))
        painter.drawRoundedRect(0, 0, self.base_width, self.full_heigth, self.corner_radius, self.corner_radius)

    def itemChange(self, change, value):

        if change == QtGui.QGraphicsItem.ItemPositionChange:
            for slot_connections in self.connections.values():
                for connection in slot_connections:
                    connection.compute_points()

        return QtGui.QGraphicsItem.itemChange(self, change, value)

    def get_content(self):

        content = self.node_info["content"]

        inputs_and_parameters_as_args = []
        inputs_and_parameters_as_kwargs = []

        for i, (slot_name, slot_tuple) in enumerate(self.input_slots.items()):
            
            slot_content = []
            slot_info = slot_tuple[0]
            slot_object = slot_tuple[1]
            slot_connections = self.connections.get(slot_object)

            # Use recursion if there are any connections,
            if slot_connections:
                # Only one input connection is allowed
                slot_connection = list(slot_connections)[0]
                slot_content = slot_connection.source_node.get_content()

            # otherwise use parameters (if expose_as_parameter is true)
            else:
                if slot_info["expose_as_parameter"]:
                    slot_content = [pe.parameter_to_content(slot_info["type"], slot_info["value"])]
                if slot_info.get("published_as") is not None:
                    slot_content = [slot_info["published_as"]]
                        # TODO: Compare the current value with gefault value
                        # and ignore it if they are same

            if slot_content:
                slot_as_arg = replace_indentated_text(["REPLACEME,\n"], "REPLACEME", slot_content)
                inputs_and_parameters_as_args.extend(slot_as_arg)
                slot_as_kwarg = replace_indentated_text(["{slot_name} : REPLACEME,\n".format(**vars())], "REPLACEME", slot_content)
                inputs_and_parameters_as_kwargs.extend(slot_as_kwarg)
                
        if inputs_and_parameters_as_args:
            inputs_and_parameters_as_args[-1] = inputs_and_parameters_as_args[-1].replace(",\n", "")

        if inputs_and_parameters_as_kwargs:
            inputs_and_parameters_as_kwargs[-1] = inputs_and_parameters_as_kwargs[-1].replace(",\n", "")

        replaced_args = replace_indentated_text(content, "//ARGS//", inputs_and_parameters_as_args)
        replaced_kwargs = replace_indentated_text(replaced_args, "//KWARGS//", inputs_and_parameters_as_kwargs)

        return [line for line in replaced_kwargs if line.strip()]

    def get_imports(self):
        
        imports = []
        imports.extend(self.node_info["description"].get("imports"))

        for i, (slot_name, slot_tuple) in enumerate(self.input_slots.items()):
            slot_connections = self.connections.get(slot_tuple[1])
            if slot_connections:
                slot_connection = list(slot_connections)[0]
                imports.extend(slot_connection.source_node.get_imports())

        return sorted(set(imports))

    def get_definitions(self):
       
        definitions = set()
        node_definitions = self.node_info["description"].get("definitions") # It's a string, not list
        if node_definitions:
            definitions.add(node_definitions)

        for i, (slot_name, slot_tuple) in enumerate(self.input_slots.items()):
            slot_connections = self.connections.get(slot_tuple[1])
            if slot_connections:
                slot_connection = list(slot_connections)[0]
                slot_definitions = slot_connection.source_node.get_definitions()
                if slot_definitions:
                    definitions.update(slot_definitions)

        return definitions

    def get_published_parameters(self):
        
        def has_uniform_parents(slot_object):

            node = slot_object.parentItem()
            for out_slot_tuple in node.output_slots.values():
                connections = node.connections.get(out_slot_tuple[1])
                if connections:
                    for connection in connections:
                        slot_info, slot_obj = connection.target_node.input_slots[connection.target_slot.name]
                        if slot_info.get("is_uniform") or has_uniform_parents(slot_obj):
                            return True
                return False

        published_parameters = {}
        for slot_name, slot_tuple in self.input_slots.items():
            if slot_tuple[0].get("published_as") is not None:
                parameter_string = ""
                if slot_tuple[0].get("is_uniform") or has_uniform_parents(slot_tuple[1]):
                    parameter_string += "uniform "
                parameter_string += slot_tuple[0]["type"] + " " + slot_tuple[0]["published_as"]
                if slot_tuple[0].get("expose_as_parameter") and slot_tuple[0]["value"] is not None:
                    parameter_string += " = " + pe.parameter_to_content(slot_tuple[0]["type"], slot_tuple[0]["value"])
                published_parameters[slot_tuple[0]["published_as"]] = parameter_string

        # Recursive invoke
        for i, (slot_name, slot_tuple) in enumerate(self.input_slots.items()):
            slot_connections = self.connections.get(slot_tuple[1])
            if slot_connections:
                slot_connection = list(slot_connections)[0]
                published_parameters.update(slot_connection.source_node.get_published_parameters())

        return published_parameters

    def get_mdl_code(self, material_name="mdl_material"):

        mdl_code = "mdl 1.3;"
        mdl_code += "\n"
        mdl_code += "\n"

        import_strings = self.get_imports()
        if import_strings:
            for import_string in import_strings:
                mdl_code += "import {import_string};".format(**vars())
                mdl_code += "\n"
            mdl_code += "\n"

        definitions = self.get_definitions()
        if definitions:
            for definition in definitions:
                mdl_code += definition
                mdl_code += "\n"
            mdl_code += "\n"

        pp = self.get_published_parameters()
        published_parameters = [pp[k] for k in sorted(pp)]
        parameters_only = [p for p in published_parameters[:] if "=" not in p]
        parameters_with_value = [p for p in published_parameters[:] if "=" in p]
        published_parameters = ", \n".join(parameters_only + parameters_with_value)
        mdl_code += "export material {material_name}({published_parameters}) =".format(**vars())
        mdl_code += "\n"
        mdl_code += "".join(self.get_content())
        mdl_code += ";"

        return mdl_code

class ConnectionItem(QtGui.QGraphicsItem):

    def __init__(self, source_slot, target_slot):
        super(self.__class__, self).__init__()

        self.source_slot = source_slot
        self.target_slot = target_slot
        self.source_node = self.source_slot.parentItem()
        self.target_node = self.target_slot.parentItem()

        # Create weak reference to the connection inside of the node
        # TODO: Should we check the slot existance here??
        self.source_node.connections[source_slot].add(self)
        self.target_node.connections[target_slot].add(self)
        self.setZValue(-1)
        self.compute_points()

    def compute_points(self):

        self.prepareGeometryChange()
        self.start_point = self.mapFromItem(self.source_slot, (QtCore.QPointF(0, 0)))
        self.end_point = self.mapFromItem(self.target_slot, (QtCore.QPointF(0, 0)))

    def generate_bezier_points(self):

        x_distance = self.end_point.x() - self.start_point.x()
        length = QtCore.QLineF(self.start_point, self.end_point).length()
        offset = math.copysign(length, x_distance)/3.0

        bezier_points   =  [QtCore.QPointF(self.start_point), 
                            QtCore.QPointF(self.start_point.x() + offset, self.start_point.y()), 
                            QtCore.QPointF(self.end_point.x() - offset, self.end_point.y()), 
                            QtCore.QPointF(self.end_point)]

        return bezier_points

    def boundingRect(self):

        p1, p2, p3, p4 = self.generate_bezier_points()
        min_x = min(p1.x(), p2.x(), p3.x(), p4.x())
        min_y = min(p1.y(), p2.y(), p3.y(), p4.y())
        max_x = max(p1.x(), p2.x(), p3.x(), p4.x())
        max_y = max(p1.y(), p2.y(), p3.y(), p4.y())
        w = max_x - min_x
        h = max_y - min_y

        return QtCore.QRectF(min_x, min_y, w, h)

    def paint(self, painter, style, widget):

        pen = QtGui.QPen(QtGui.QColor(0, 64, 0, 128))
        pen.setWidth(2)
        painter.setPen(pen)

        p1, p2, p3, p4 = self.generate_bezier_points()

        path = QtGui.QPainterPath()
        path.moveTo(p1)
        path.cubicTo(p2, p3, p4)
        painter.drawPath(path)

    def mouseDoubleClickEvent(self, event):

        if event.button()==QtCore.Qt.LeftButton:
            self.delete_it()

    def delete_it(self):

        for view in self.scene().views():
            view.connections.remove(self)
        self.scene().removeItem(self)

class NodeEditor(QtGui.QGraphicsView):

    def __init__(self):

        # Call parent's constructor
        super(self.__class__, self).__init__()

        # Set-up QGraphicsView
        self.setAcceptDrops(True)
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setDragMode(QtGui.QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        # Add scene
        scene = QtGui.QGraphicsScene(self)
        scene.setSceneRect(-5000, -5000, 10000, 10000)
        scene.setBackgroundBrush(QtGui.QColor(243, 240, 230))
        self.setScene(scene)

        # Parameters layout
        self.parameter_editor = pe.ParameterEditor(parent=self)
        self.setLayout(self.parameter_editor)

        # Attributes
        self.connections = [] # List of 'ConnectionItem' objects
        self.available_nodes = scan_available_nodes(NODE_TYPES_FOLDER)
        self.message_widget = QtGui.QTextEdit(self)
        self.message_widget.setWindowFlags(QtCore.Qt.Window)
        self.scale_factor = 1.0
        self.last_used_folder = os.path.expanduser("~")


    def check_connection_validity(self, source_slot, target_slot):

        # Check that the output slot type corresponds to the input slot type
        if source_slot.type != target_slot.type:
            return False
        
        # Check that the nodes we try to connect are different
        source_node = source_slot.parentItem()
        target_node = target_slot.parentItem()
        if source_node == target_node:
            log.error("Connection creation error. Please use different nodes to create new connection.")
            return False

        # Check that we try to connect output and input slots
        target_node_inputs = [el[1] for el in target_node.input_slots.values()]
        source_node_outputs = [el[1] for el in source_node.output_slots.values()]
        if not ((source_slot in source_node_outputs)\
        and (target_slot in target_node_inputs)):
            log.error("Connection creation error. Only output->input connections are allowed.")
            return False

        # Check that we do not connect varying attribute to uniform attribute.
        if source_node.output_slots[source_slot.name][0].get("is_varying")\
        and target_node.input_slots[target_slot.name][0].get("is_uniform"):
            log.error("Connection creation error. Connection varying output to uniform input is not allowed.")
            return False
            
        return True

    def check_connection_existance(self, source_slot, target_slot):

        for connection in self.connections:
            if (connection.source_slot==source_slot) and (connection.target_slot==target_slot):
                return True
        return False

    def show_node_content(self, node):

        self.message_widget.setText("".join(node.get_content()))
        self.message_widget.setWindowTitle("Node Content Viewer")
        self.message_widget.setWindowModality(QtCore.Qt.WindowModal)
        self.message_widget.show()

    def show_mdl_code(self, node):

        self.message_widget.setText(node.get_mdl_code())
        self.message_widget.setWindowTitle("MDL Code Viewer")
        self.message_widget.setWindowModality(QtCore.Qt.WindowModal)
        self.message_widget.show()

    def save_mdl_material(self, node):

        result = QtGui.QFileDialog.getSaveFileName(self, "Save MDL Material...", os.path.expanduser("~"), "MDL Files (*.mdl)")
        file_name = result[0]
        if file_name:
            with open(file_name, "w") as f:
                f.write(node.get_mdl_code(material_name=Path(file_name).namebase))

    def create_right_click_menu(self, clicked_node, event_scene_position, clicked_slot=None):

        node_categories = {} # "category_name" : menu_item_object
        nodes_by_category = defaultdict(dict)

        rcl_menu = QtGui.QMenu()
        create_menu = QtGui.QMenu("Create")
        rcl_menu.addMenu(create_menu)

        for node_type, node_info in sorted(self.available_nodes.items()):
            category = node_info["description"]["category"]
            nodes_by_category[category][node_type] = node_info

        for category in sorted(nodes_by_category):
            for node_type in sorted(nodes_by_category[category]):
                # Create category menu item if necessary
                if category not in node_categories:
                    category_menu_item = QtGui.QMenu(category)
                    create_menu.addMenu(category_menu_item)
                    node_categories[category] = category_menu_item
                action = QtGui.QAction(node_type, category_menu_item)
                action.triggered.connect(partial(self.create_node, node_type=node_type, scene_position=event_scene_position))
                node_categories[category].addAction(action)

        rcl_menu.addSeparator()

        action = QtGui.QAction("Show Content", rcl_menu)
        action.setEnabled(clicked_node is not None)
        action.triggered.connect(partial(self.show_node_content, node=clicked_node))
        rcl_menu.addAction(action)

        action = QtGui.QAction("Show MDL Code", rcl_menu)
        action.setEnabled(clicked_node is not None and clicked_node.node_type=="material")
        action.triggered.connect(partial(self.show_mdl_code, node=clicked_node))
        rcl_menu.addAction(action)

        action = QtGui.QAction("Save MDL Material...", rcl_menu)
        action.setEnabled(clicked_node is not None and clicked_node.node_type=="material")
        action.triggered.connect(partial(self.save_mdl_material, node=clicked_node))
        rcl_menu.addAction(action)

        rcl_menu.addSeparator()
        if clicked_slot is not None:
            slot_tuple = clicked_node.input_slots.get(clicked_slot.name)
            if slot_tuple: # If it's an input slot
                if slot_tuple[0].get("published_as") is None:
                    action = QtGui.QAction("Publish Parameter...", rcl_menu)
                    action.triggered.connect(partial(self.publish_parameter, clicked_node=clicked_node, clicked_slot=clicked_slot))
                    rcl_menu.addAction(action)
                else:
                    action = QtGui.QAction("Rename Published Parameter...", rcl_menu)
                    action.triggered.connect(partial(self.rename_published_parameter, clicked_node=clicked_node, clicked_slot=clicked_slot))
                    rcl_menu.addAction(action)
                    action = QtGui.QAction("Unpublish Parameter", rcl_menu)
                    action.triggered.connect(partial(self.unpublish_parameter, clicked_node=clicked_node, clicked_slot=clicked_slot))
                    rcl_menu.addAction(action)
                rcl_menu.addSeparator()

        action = QtGui.QAction("Delete Node", rcl_menu)
        action.setEnabled(clicked_node is not None)
        action.triggered.connect(partial(self.delete_node, node=clicked_node))
        rcl_menu.addAction(action)

        return rcl_menu

    def create_node(self, node_type, scene_position=None):

        new_node = NodeItem(node_type, self.available_nodes[node_type])
        if scene_position:
            new_node.setPos(scene_position)
        self.scene().addItem(new_node)
        self.attach_connection_request_function_to_slots(new_node)
        # Since every time some overload is loaded 
        # all of the node slots are recreated,
        # we need to reconnect slot's 'connection_request' signals
        # to the 'add_connection' function again.
        new_node.overload_changed.connect(self.attach_connection_request_function_to_slots)

        return new_node

    def delete_node(self, node):
        
        node.clear_node()
        self.parameter_editor.plug_node(None)
        self.scene().removeItem(node)

    def attach_connection_request_function_to_slots(self, node):

        input_slot_objects = [el[1] for el in node.input_slots.values()]
        output_slot_objects = [el[1] for el in node.output_slots.values()]
        for slot_object in input_slot_objects + output_slot_objects:
            if slot_object:
                slot_object.connection_request.connect(self.add_connection)

    def add_connection(self, source_slot, target_slot):

        if not self.check_connection_existance(source_slot, target_slot):
            if self.check_connection_validity(source_slot, target_slot):
                new_connection = ConnectionItem(source_slot, target_slot)
                self.scene().addItem(new_connection)
                self.connections.append(new_connection)

    def publish_parameter(self, clicked_node, clicked_slot):
        # TODO: break connections if any
        inp_dialog = QtGui.QInputDialog()
        inp_dialog.setInputMode(QtGui.QInputDialog.TextInput)
        user_text = inp_dialog.getText(self ,"Publish Parameter Dialog", "Please enter the parameter publishing name:")[0]
        if user_text:
            # TODO: Check name uniqueness
            clicked_node.input_slots[clicked_slot.name][0]["published_as"] = user_text
            clicked_slot.publish(user_text)

    def rename_published_parameter(self, clicked_node, clicked_slot):

        inp_dialog = QtGui.QInputDialog()
        inp_dialog.setInputMode(QtGui.QInputDialog.TextInput)
        current_name = clicked_node.input_slots[clicked_slot.name][0]["published_as"]
        user_text = inp_dialog.getText(self ,"Rename Published Parameter Dialog", "Please enter the new name of published parameter:", text=current_name)[0]
        if user_text:
            # TODO: Check name uniqueness
            clicked_node.input_slots[clicked_slot.name][0]["published_as"] = user_text
            clicked_slot.publish(user_text)

    def unpublish_parameter(self, clicked_node, clicked_slot):
        
        clicked_node.input_slots[clicked_slot.name][0]["published_as"] = None
        clicked_slot.unpublish()
        self.scene().update()

    def new_graph(self):

        self.connections = []
        self.scene().clear()

    def load_graph(self):

        self.new_graph()
        self.append_graph()

    def append_graph(self):

        result = QtGui.QFileDialog.getOpenFileName(self, "Select MDL Node Graph...", self.last_used_folder, "MDL Node Graph Files (*.mng)")

        file_name = result[0]
        
        if not file_name:
            return

        self.last_used_folder = Path(file_name).dirname()
        with open(file_name) as f:
            graph_info = json.load(f)

            for node_id, node_info in graph_info["nodes_info"].items():
                new_node = self.create_node(node_info["type"])
                new_node.current_overload = node_info["overload"]
                new_node.load_overload_info()
                new_node.setPos(*node_info["position"])
                if node_info.get("parameters"):
                    for parameter_name, parameter_info in node_info["parameters"].items():
                        slot_info = new_node.input_slots[parameter_name][0]
                        slot_object = new_node.input_slots[parameter_name][1]
                        if parameter_info.get("expose_as_parameter"):
                            slot_info["value"] = parameter_info["value"]
                        if parameter_info.get("published_as"):
                            slot_info["published_as"] = parameter_info["published_as"]
                            slot_object.publish(slot_info["published_as"])
                            
                graph_info["nodes_info"][node_id] = new_node

            for source_node_id, source_slot_name, \
            target_node_id, target_slot_name \
            in graph_info["connections_info"]:
                source_slot = graph_info["nodes_info"][source_node_id].output_slots[source_slot_name][1]
                target_slot = graph_info["nodes_info"][target_node_id].input_slots[target_slot_name][1]
                self.add_connection(source_slot, target_slot)

    def save_graph(self):

        nodes_info = {}

        for node in self.items():
            if type(node)==NodeItem:
                node_dict = {}
                node_dict["type"] = node.node_type
                node_dict["position"] = node.pos().x(), node.pos().y()
                node_dict["overload"] = node.current_overload
                node_dict["parameters"] = {}
                for slot_name, slot_tuple in node.input_slots.items():
                    slot_info = slot_tuple[0]
                    if slot_info["expose_as_parameter"] or slot_info.get("published_as"):
                        node_dict["parameters"][slot_name] = slot_info
                # Save patameter values
                nodes_info[str(id(node))] = node_dict

        connections_info = []

        for connection in self.connections:
            connection_info = str(id(connection.source_node)), connection.source_slot.name, str(id(connection.target_node)), connection.target_slot.name
            connections_info.append(connection_info)

        graph_info = {}
        graph_info["nodes_info"] = nodes_info
        graph_info["connections_info"] = connections_info

        result = QtGui.QFileDialog.getSaveFileName(self, "Save MDL Node Graph...", self.last_used_folder, "MDL Node Graph Files (*.mng)")
        file_name = result[0]
        if not file_name: return

        self.last_used_folder = Path(file_name).dirname()
        with open(file_name, "w") as f:
            json.dump(graph_info, f, indent=4)

    def mousePressEvent(self, event):

        def find_node_item(item):

            if not item:
                return None

            elif isinstance(item, NodeItem):
                return item

            parent = item.parentItem()

            if not parent:
                return None

            return find_node_item(parent)

        super(NodeEditor, self).mousePressEvent(event)

        if event.button()==QtCore.Qt.RightButton:
            event_scene_position = self.mapToScene(event.pos())
            clicked_item = self.itemAt(event.pos())
            clicked_node = find_node_item(clicked_item)

            if isinstance(clicked_item, SlotItem):
                self.rcl_menu = self.create_right_click_menu(clicked_node, event_scene_position, clicked_slot=clicked_item)
            else:
                self.rcl_menu = self.create_right_click_menu(clicked_node, event_scene_position)

            self.rcl_menu.popup(self.mapToGlobal(event.pos()))
            self.parameter_editor.plug_node(clicked_node)

        elif event.button() in (QtCore.Qt.LeftButton, QtCore.Qt.MiddleButton):
            clicked_item = self.itemAt(event.pos())
            clicked_node = find_node_item(clicked_item)
            self.parameter_editor.plug_node(clicked_node)
        
        self.scene().update()

    def wheelEvent(self, event):

        if event.delta() > 0:
            if self.scale_factor<3:
                self.scale_factor *= 1.01
                self.scale(1.05, 1.05)
        else:
            if self.scale_factor>0.5:
                self.scale_factor *= 0.99
                self.scale(0.9, 0.9)


        # super(NodeEditor, self).wheelEvent(event)

class NodeEditorWindow(QtGui.QMainWindow):

    def __init__(self, parent=None):

        super(self.__class__, self).__init__(parent)
        self.setWindowIcon(QtGui.QIcon(ICON_PATH))
        self.setWindowTitle("MDL Node Editor")
        self.node_editor = NodeEditor()
        self.setCentralWidget(self.node_editor)
        self.add_menu_bar()
        self.show()

    def add_menu_bar(self):
        
        menu = self.menuBar().addMenu("File")

        action = menu.addAction("New MDL Graph...")
        action.triggered.connect(self.node_editor.new_graph)

        action = menu.addAction("Load MDL Graph...")
        action.triggered.connect(self.node_editor.load_graph)

        action = menu.addAction("Append MDL Graph...")
        action.triggered.connect(self.node_editor.append_graph)

        action = menu.addAction("Save MDL Graph...")
        action.triggered.connect(self.node_editor.save_graph)

        menu.addSeparator()

        action = menu.addAction("Close")
        action.triggered.connect(QtGui.qApp.quit)

        menu = self.menuBar().addMenu("Help")

        action = menu.addAction("About")
        action.triggered.connect(self.show_about)

    def show_about(self):

        self.about_dialog = QtGui.QMessageBox(self)
        title = "About"
        text = "<h2>MDL Node Editor</h2><br/><br/>Version: 0.1.0<br/><br/>2017, GNU GPLv3 license<br/><br/>Author: Alexander Kasperovich<br/>Contacts: <a href='www.linkedin.com/in/regexus'>LinkedIn</a>, <a href='https://github.com/regexus'>GitHub</a><br/><br/>More <a href='http://www.nvidia.com/object/material-definition-language.html'>info</a> about MDL."
        self.about_dialog.about(self, title, text)

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    new = NodeEditorWindow()
    sys.exit(app.exec_())