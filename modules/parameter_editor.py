import os
import json
from PySide import QtCore, QtGui
import logging as log

log.basicConfig(level=log.DEBUG, format="%(levelname)s from '%(module)s' : %(message)s")

ROOT_FOLDER = os.path.dirname(os.path.dirname(__file__))
ENUMS_INFO = json.load(open(os.path.join(ROOT_FOLDER, "nodes", "enums.info")))

def parameter_to_content(parameter_type, parameter_value):
    """The 'parameter_value' should be json-serialized."""

    value = parameter_value

    if parameter_type=="bool":
        return str(value).lower()

    elif parameter_type=="string":
        return '"{0}"'.format(value)

    elif parameter_type in ["int", "float", "double"]:
        return "{parameter_type}({0})".format(value, parameter_type=parameter_type)

    elif parameter_type=="float2":
        return "{parameter_type}({0}, {1})".format(*value, parameter_type=parameter_type)

    elif parameter_type in ["float3", "color"]:
        return "{parameter_type}({0}, {1}, {2})".format(*value, parameter_type=parameter_type)

    elif parameter_type in ENUMS_INFO:
        return "{module_name}::{0}".format(value, module_name=ENUMS_INFO[parameter_type]["module"])

    else:
        log.error("Unknown parameter type!")

class ParameterEditorEnum(QtGui.QWidget):

    def __init__(self, parameter_name, parameter_type, node_item, parent=None):

        super(self.__class__, self).__init__(parent)

        self.node_item = node_item
        self.parameter_name = parameter_name 

        label = QtGui.QLabel("{parameter_name} (enum)".format(**vars()))

        self.combo_box = QtGui.QComboBox()
        for enum_value in ENUMS_INFO[parameter_type]["values"]:
            self.combo_box.addItem(enum_value)

        # Create layout and add widgets
        self.setLayout(QtGui.QVBoxLayout())
        self.layout().addWidget(label)
        self.layout().addWidget(self.combo_box)

        self.get_value_from_node()
        self.combo_box.activated.connect(self.assign_value_to_node)

    def get_value_from_node(self):

        parameter_value = self.node_item.input_slots[self.parameter_name][0]["value"]
        for i in range(self.combo_box.count()):
            if self.combo_box.itemText(i) == parameter_value:
                self.combo_box.setCurrentIndex(i)

    def assign_value_to_node(self):

        self.node_item.input_slots[self.parameter_name][0]["value"] = self.combo_box.currentText()

class ParameterEditorBool(QtGui.QWidget):

    def __init__(self, parameter_name, node_item, parent=None):

        super(self.__class__, self).__init__(parent)
        self.node_item = node_item
        self.parameter_name = parameter_name 

        label = QtGui.QLabel("{parameter_name} (bool)".format(**vars()))

        self.combo_box = QtGui.QComboBox()
        self.combo_box.setMaximumWidth(75)
        self.combo_box.setMinimumWidth(75)
        self.combo_box.addItem("false")
        self.combo_box.addItem("true")

        # Create layout and add widgets
        self.setLayout(QtGui.QVBoxLayout())
        self.layout().addWidget(label)
        self.layout().addWidget(self.combo_box)

        self.get_value_from_node()
        self.combo_box.activated.connect(self.assign_value_to_node)

    def get_value_from_node(self):

        parameter_value = self.node_item.input_slots[self.parameter_name][0]["value"]
        if parameter_value == False:
            self.combo_box.setCurrentIndex(0)
        elif parameter_value == True:
            self.combo_box.setCurrentIndex(1)

    def assign_value_to_node(self):

        if self.combo_box.currentIndex() == 0:
            self.node_item.input_slots[self.parameter_name][0]["value"] = False
        elif self.combo_box.currentIndex() == 1:
            self.node_item.input_slots[self.parameter_name][0]["value"] = True

class ParameterEditorString(QtGui.QWidget):

    def __init__(self, parameter_name, node_item, parent=None):

        super(self.__class__, self).__init__(parent)
        self.node_item = node_item
        self.parameter_name = parameter_name 

        label = QtGui.QLabel("{parameter_name} (string)".format(**vars()))

        self.line_edit = QtGui.QLineEdit()
        self.line_edit.setMaximumWidth(150)

        # Create layout and add widgets
        self.setLayout(QtGui.QVBoxLayout())
        self.layout().addWidget(label)
        self.layout().addWidget(self.line_edit)

        self.get_value_from_node()
        self.line_edit.textChanged.connect(self.assign_value_to_node)

    def get_value_from_node(self):

        parameter_value = self.node_item.input_slots[self.parameter_name][0]["value"]
        self.line_edit.setText(parameter_value)

    def assign_value_to_node(self, new_value):

        self.node_item.input_slots[self.parameter_name][0]["value"] = str(new_value).replace("\\", "/")

class ParameterEditorFloat(QtGui.QWidget):

    def __init__(self, parameter_name, node_item, parent=None):

        super(self.__class__, self).__init__(parent)
        self.node_item = node_item
        self.parameter_name = parameter_name 

        label = QtGui.QLabel("{parameter_name} (float)".format(**vars()))

        self.line_edit = QtGui.QLineEdit()
        self.line_edit.setMaximumWidth(75)
        self.line_edit.setMinimumWidth(75)

        # Create layout and add widgets
        self.setLayout(QtGui.QVBoxLayout())
        self.layout().addWidget(label)
        self.layout().addWidget(self.line_edit)

        self.get_value_from_node()
        self.line_edit.textChanged.connect(self.assign_value_to_node)

    def get_value_from_node(self):

        parameter_value = self.node_item.input_slots[self.parameter_name][0]["value"]
        self.line_edit.setText(str(parameter_value))

    def assign_value_to_node(self, new_value):

        self.node_item.input_slots[self.parameter_name][0]["value"] = float(new_value)

class ParameterEditorFloat2(QtGui.QWidget):

    def __init__(self, parameter_name, node_item, parent=None):

        super(self.__class__, self).__init__(parent)
        self.node_item = node_item
        self.parameter_name = parameter_name 

        label = QtGui.QLabel("{parameter_name} (float2)".format(**vars()))

        self.line_edit_x = QtGui.QLineEdit()
        self.line_edit_x.setMaximumWidth(75)
        self.line_edit_x.setMinimumWidth(75)
        self.line_edit_y = QtGui.QLineEdit()
        self.line_edit_y.setMaximumWidth(75)
        self.line_edit_y.setMinimumWidth(75)

        # Create layout and add widgets
        self.setLayout(QtGui.QVBoxLayout())
        self.layout().addWidget(label)
        self.layout().addWidget(self.line_edit_x)
        self.layout().addWidget(self.line_edit_y)

        self.get_value_from_node()
        self.line_edit_x.textChanged.connect(self.assign_x_value_to_node)
        self.line_edit_y.textChanged.connect(self.assign_y_value_to_node)


    def get_value_from_node(self):

        parameter_value = self.node_item.input_slots[self.parameter_name][0]["value"]
        self.line_edit_x.setText(str(parameter_value[0]))
        self.line_edit_y.setText(str(parameter_value[1]))

    def assign_x_value_to_node(self, new_value):

        self.node_item.input_slots[self.parameter_name][0]["value"][0] = float(new_value)

    def assign_y_value_to_node(self, new_value):

        self.node_item.input_slots[self.parameter_name][0]["value"][1] = float(new_value)

class ParameterEditorFloat3(QtGui.QWidget):

    def __init__(self, parameter_name, node_item, parent=None):

        super(self.__class__, self).__init__(parent)
        self.node_item = node_item
        self.parameter_name = parameter_name 

        label = QtGui.QLabel("{parameter_name} (float3)".format(**vars()))

        self.line_edit_x = QtGui.QLineEdit()
        self.line_edit_x.setMaximumWidth(75)
        self.line_edit_x.setMinimumWidth(75)
        self.line_edit_y = QtGui.QLineEdit()
        self.line_edit_y.setMaximumWidth(75)
        self.line_edit_y.setMinimumWidth(75)
        self.line_edit_z = QtGui.QLineEdit()
        self.line_edit_z.setMaximumWidth(75)
        self.line_edit_z.setMinimumWidth(75)

        # Create layout and add widgets
        self.setLayout(QtGui.QVBoxLayout())
        self.layout().addWidget(label)
        self.layout().addWidget(self.line_edit_x)
        self.layout().addWidget(self.line_edit_y)
        self.layout().addWidget(self.line_edit_z)

        self.get_value_from_node()
        self.line_edit_x.textChanged.connect(self.assign_x_value_to_node)
        self.line_edit_y.textChanged.connect(self.assign_y_value_to_node)
        self.line_edit_z.textChanged.connect(self.assign_z_value_to_node)

    def get_value_from_node(self):

        parameter_value = self.node_item.input_slots[self.parameter_name][0]["value"]
        self.line_edit_x.setText(str(parameter_value[0]))
        self.line_edit_y.setText(str(parameter_value[1]))
        self.line_edit_z.setText(str(parameter_value[2]))

    def assign_x_value_to_node(self, new_value):

        self.node_item.input_slots[self.parameter_name][0]["value"][0] = float(new_value)

    def assign_y_value_to_node(self, new_value):

        self.node_item.input_slots[self.parameter_name][0]["value"][1] = float(new_value)

    def assign_z_value_to_node(self, new_value):

        self.node_item.input_slots[self.parameter_name][0]["value"][2] = float(new_value)

class ParameterEditorColor(QtGui.QWidget):

    def __init__(self, parameter_name, node_item, parent=None):

        super(self.__class__, self).__init__(parent)
        self.node_item = node_item
        self.parameter_name = parameter_name 

        label = QtGui.QLabel("{parameter_name} (color)".format(**vars()))

        # Color chip
        self.color_square = QtGui.QLabel()
        self.color_square.setMaximumSize(50, 50)
        self.color_square.setMinimumSize(50, 50)
        self.color_square.setAutoFillBackground(True)

        # Create layout and add widgets
        self.setLayout(QtGui.QVBoxLayout())
        self.layout().addWidget(label)
        self.layout().addWidget(self.color_square)

        self.get_value_from_node()
        self.color_square.mousePressEvent = lambda event: self.assign_value_to_node()

        # self.line_edit.textChanged.connect(self.assign_value_to_node)

    def get_value_from_node(self):

        parameter_value = self.node_item.input_slots[self.parameter_name][0]["value"]
        color = QtGui.QColor.fromRgbF(min(parameter_value[0], 1.0), min(parameter_value[1], 1.0), min(parameter_value[2], 1.0))
        r = color.toRgb().red()
        g = color.toRgb().green()
        b = color.toRgb().blue()
        self.color_square.setStyleSheet("background-color:rgbf({r},{g},{b});".format(**vars()))


    def assign_value_to_node(self):

        color = QtGui.QColorDialog.getColor(QtCore.Qt.white, self, "Select Color", QtGui.QColorDialog.DontUseNativeDialog);
        r = color.toRgb().red()
        g = color.toRgb().green()
        b = color.toRgb().blue()
        self.color_square.setStyleSheet("background-color:rgbf({r},{g},{b});".format(**vars()))
        self.node_item.input_slots[self.parameter_name][0]["value"] = list(color.getRgbF()[:3])

class ParameterEditor(QtGui.QHBoxLayout):

    # TODO: Do not show connected attributes

    def __init__(self, node_item=None, parent=None):

        super(self.__class__, self).__init__(parent)
        self.parameter_editors_layout = QtGui.QVBoxLayout()
        self.addLayout(self.parameter_editors_layout)
        self.plug_node(node_item)

    def clear_layout(self, layout):

        if layout is None: 
            return

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                self.clear_layout(item.layout())

    def plug_node(self, node_item):

        # Attributes
        self.editors = []

        # Recrete the layout
        self.clear_layout(self.parameter_editors_layout)

        # Just leave it clean if nothing comes in
        if node_item is None:
            return

        # Add widget name
        widget_name_label = QtGui.QLabel("Node Parameters")
        f = widget_name_label.font()
        f.setBold(True)
        widget_name_label.setFont(f)
        self.parameter_editors_layout.addWidget(widget_name_label)

        # Get connected slots, to avoid showing them as parameters
        connected_slots = set()
        for slot, connections in node_item.connections.items():
            if slot.is_parameter and len(connections)>0:
                connected_slots.add(slot.name)

        for slot_name, slot_tuple in node_item.input_slots.items():

            parameter_name = slot_tuple[0]["name"]
            parameter_type = slot_tuple[0]["type"]

            if not slot_tuple[0]["expose_as_parameter"]:
                continue
                
            if parameter_name in connected_slots:
                continue

            if parameter_type in ENUMS_INFO:
                editor = ParameterEditorEnum(parameter_name, parameter_type, node_item)
                self.editors.append(editor)
                self.parameter_editors_layout.addWidget(editor)
            elif parameter_type == "bool":
                editor = ParameterEditorBool(parameter_name, node_item)
                self.editors.append(editor)
                self.parameter_editors_layout.addWidget(editor)
            elif parameter_type == "string":
                editor = ParameterEditorString(parameter_name, node_item)
                self.editors.append(editor)
                self.parameter_editors_layout.addWidget(editor)
            elif parameter_type in ("int", "float", "double"):
                editor = ParameterEditorFloat(parameter_name, node_item)
                self.editors.append(editor)
                self.parameter_editors_layout.addWidget(editor)
            elif parameter_type in ("int2", "float2", "double2"):
                editor = ParameterEditorFloat2(parameter_name, node_item)
                self.editors.append(editor)
                self.parameter_editors_layout.addWidget(editor)
            elif parameter_type in ("int3", "float3", "double3"):
                editor = ParameterEditorFloat3(parameter_name, node_item)
                self.editors.append(editor)
                self.parameter_editors_layout.addWidget(editor)
            elif parameter_type == "color":
                editor = ParameterEditorColor(parameter_name, node_item)
                self.editors.append(editor)
                self.parameter_editors_layout.addWidget(editor)

        self.parameter_editors_layout.addStretch(100)
        self.layout().addStretch(100)
