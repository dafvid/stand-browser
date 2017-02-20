# -*- coding: utf-8 -*-
"""
/***************************************************************************
 StandBrowser
                                 A QGIS plugin
 Browse forests stand
                              -------------------
        begin                : 2017-02-18
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Magnus Homann
        email                : magnus@homann.se
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, Qt
from PyQt4.QtGui import QAction, QIcon
# Initialize Qt resources from file resources.py
import resources

# Import the code for the DockWidget
from stand_browser_dockwidget import StandBrowserDockWidget
import os.path

# Import various QGIs classes
from qgis.core import QgsMapLayer, QgsMapLayerRegistry, QgsFeatureRequest

class StandBrowser:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'StandBrowser_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Stand Browser')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'StandBrowser')
        self.toolbar.setObjectName(u'StandBrowser')

        #print "** INITIALIZING StandBrowser"

        self.pluginIsActive = False
        self.dockwidget = None

        self.layer = ""
        self.layerFeatureIds = []
        self.layerFeatureIdx = 0
        self.layerActiveFeature = None
        
    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('StandBrowser', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action


    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/StandBrowser/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Open browser...'),
            callback=self.run,
            parent=self.iface.mainWindow())

    #--------------------------------------------------------------------------

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""

        #print "** CLOSING StandBrowser"

        # disconnects
        self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)

        # remove this statement if dockwidget is to remain
        # for reuse if plugin is reopened
        # Commented next statement since it causes QGIS crashe
        # when closing the docked window:
        # self.dockwidget = None

        self.pluginIsActive = False


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        #print "** UNLOAD StandBrowser"

        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&Stand Browser'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    #--------------------------------------------------------------------------

    def update_active_layer(self):
        """Select active layer from the layer selector"""

        self.layer = ""
        self.layerFeatureIds = []
        self.layerFeatureIdx = 0
        self.layerActiveFeature = None

        layer_idx = self.dockwidget.cbLayer.currentIndex()
        if layer_idx < 0:
            return
        layer_id = self.dockwidget.cbLayer.itemData(layer_idx)
        self.layer = QgsMapLayerRegistry.instance().mapLayer(layer_id)
        self.layerFeatureIds = [f.id() for f in self.layer.getFeatures()]
        feature_id = self.layerFeatureIds[self.layerFeatureIdx]
        self.layerActiveFeature = next(self.layer.getFeatures(QgsFeatureRequest().setFilterFid(feature_id)))
        self.dockwidget.leActive.setText(self.layerActiveFeature.attribute('standid'))
        
    def update_active_feature(self):
        """Select active feature from the feature selector"""

        feature_iter = self.layer.getFeatures(QgsFeatureRequest().setFilterExpression( u'"standid" = \''+self.dockwidget.leActive.text()+'\'' ))
        # If feature_iter is empty, no such standid is found so we do nothing.
        for f in feature_iter:
            self.layerActiveFeature = f
            self.layerFeatureIdx = self.layerFeatureIds.index(f.id())
            # Zoom to new feature and select it.
            self.layer.setSelectedFeatures([self.layerFeatureIds[self.layerFeatureIdx]])
            if not self.iface.mapCanvas().extent().contains(f.geometry().boundingBox()):
                self.iface.mapCanvas().panToSelected(self.layer)
            if not self.iface.mapCanvas().extent().contains(f.geometry().boundingBox()):
                self.iface.mapCanvas().setExtent(f.geometry().boundingBox())
            self.iface.mapCanvas().refresh()
            break;
    
    def pb_next_stand(self):
        """Find next stand in layer"""

        self.layerFeatureIdx =  self.layerFeatureIdx + 1
        if self.layerFeatureIdx == len(self.layerFeatureIds):
            self.layerFeatureIdx = 0
            
        feature_id = self.layerFeatureIds[self.layerFeatureIdx]
        self.layerActiveFeature = next(self.layer.getFeatures(QgsFeatureRequest().setFilterFid(feature_id)))
        self.dockwidget.leActive.setText(self.layerActiveFeature.attribute('standid'))
        self.update_active_feature()
        
    def pb_prev_stand(self):
        """Find previous stand in layer"""

        self.layerFeatureIdx =  self.layerFeatureIdx - 1
        if self.layerFeatureIdx < 0:
            self.layerFeatureIdx = len(self.layerFeatureIds)-1
            
        feature_id = self.layerFeatureIds[self.layerFeatureIdx]
        self.layerActiveFeature = next(self.layer.getFeatures(QgsFeatureRequest().setFilterFid(feature_id)))
        self.dockwidget.leActive.setText(self.layerActiveFeature.attribute('standid'))
        self.update_active_feature()        
        
    def run(self):
        """Run method that loads and starts the plugin"""

        if not self.pluginIsActive:
            self.pluginIsActive = True

            #print "** STARTING StandBrowser"

            # dockwidget may not exist if:
            #    first run of plugin
            #    removed on close (see self.onClosePlugin method)
            if self.dockwidget == None:
                # Create the dockwidget (after translation) and keep reference
                self.dockwidget = StandBrowserDockWidget()

            # connect to provide cleanup on closing of dockwidget
            self.dockwidget.closingPlugin.connect(self.onClosePlugin)

            # show the dockwidget
            # TODO: fix to allow choice of dock location
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dockwidget)
            self.dockwidget.show()

            layers = self.iface.legendInterface().layers()
            self.dockwidget.cbLayer.clear()
            for layer in layers:
                # Check if the layer is a vector layer and
                # includes a 'standid' field
                if layer.type() == QgsMapLayer.VectorLayer:
                    for f in layer.fields():
                        if f.name() == 'standid':
                            self.dockwidget.cbLayer.addItem(layer.name(), layer.id())
                            break
            self.update_active_layer()
            self.update_active_feature()

            # Connect signals from buttons in widget
            self.dockwidget.leActive.editingFinished.connect(self.update_active_feature)
            self.dockwidget.pbNext.clicked.connect(self.pb_next_stand)
            self.dockwidget.pbPrev.clicked.connect(self.pb_prev_stand)
