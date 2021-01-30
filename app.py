import os
from flask import Flask, send_from_directory
from urllib.parse import quote as urlquote

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State, ALL, MATCH
import plotly.graph_objects as go
from plotutils import *
from sfsutils import parse_savefile
from iniutils import ini_to_system
from imageutils import map_url
from base64 import b64decode
from collections import OrderedDict

import jsonpickle
import math
import numpy as np
from orbit import Orbit
from body import Body
from craft import Craft

DOWNLOAD_DIRECTORY = "/tmp/app_generated_files"

if not os.path.exists(DOWNLOAD_DIRECTORY):
    os.makedirs(DOWNLOAD_DIRECTORY)

#external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

server = Flask(__name__)
app = dash.Dash(__name__, # external_stylesheets=external_stylesheets,
                server=server)

app.title='KSP Trajectory Illustrator'

#%% read solar system data
infile = open('kerbol_system.json','r')
kerbol_system = jsonpickle.decode(infile.read())
infile.close()
infile = open('outer_planets_system.json','r')
outer_planets_system = jsonpickle.decode(infile.read())
infile.close()
infile = open('sol_system.json','r')
sol_system = jsonpickle.decode(infile.read())
infile.close()

#%%

def name_options(objectList):
    nameOptions = []
    for ob in objectList:
        nameOptions.append(ob.name) 
    return [{'label': i, 'value': i} for i in nameOptions]

def range_in_range(start1, end1, start2, end2):
    
    if start2 is None:
        start2 = 0
    if end2 is None:
        end2 = math.inf
    
    if (start1 >= start2 and start1 < end2) or      \
       (end1 >= start2 and end1 < end2) or          \
       (start1 <= start2 and end1 >= end2):
           
        return True
    
    else:
        return False

def add_maneuver_node(nodesList, num, burn=None):
    if burn is None:
        burn = [None, None, None, None]
    nodesList.append(html.Label('Maneuver node '+str(num)))
    nodesList.append(dcc.Input(type='number',
                               placeholder='Prograde (m/s)',
                               value=burn[0]))
    nodesList.append(dcc.Input(type='number',
                               placeholder='Normal (m/s)',
                               value=burn[1]))
    nodesList.append(dcc.Input(type='number',
                               placeholder='Radial (m/s)',
                               value=burn[2]))
    nodesList.append(dcc.Input(type='number',
                               placeholder='UT (s)',
                               value=burn[3]))

def make_new_craft_tab(label, index, system,
                        primName=None, a=0, ecc=0, inc=0, argp=0, lan=0,
                        mo=0, epoch=0,
                        maneuverNodes=None):
    
    if not maneuverNodes is None:
        numNodes = len(maneuverNodes)
    else:
        numNodes = 0
    
    newTab = dcc.Tab(id = {'type': 'craft-tab',
                           'index': index},
                    label=label,
                    value=label, 
                    className='control-tab',
                    children=[
                html.Div(style={'padding-top' : 25}, children=[         #0
                    html.Button(children = 'Delete Craft',
                            className = 'button-primary',
                            id = {'type': 'deleteCraft-button',
                                  'index': index},
                            n_clicks = 0,
                            ),
                    ]),
                html.H3('Plot Style'),                                  #1
                html.Div(className='row', children = [                  #2
                    html.Div(className='six columns', children=[      #0
                        html.Label('Name'),                         #0
                        dcc.Input(id={'type': 'name-input',         #1
                                      'index': index},
                                  type='text',
                                  value=label),
                        ]),
                    html.Div(className='six columns', children=[     #1
                        html.Label('Color (RGB)'),                #0
                        dcc.Input(id={'type': 'red-input',        #1
                                      'index': index},
                                  type='number',
                                  min=0,
                                  max=255,
                                  value=255),
                        dcc.Input(id={'type': 'grn-input',        #2
                                      'index': index},
                                  type='number',
                                  min=0,
                                  max=255,
                                  value=255),
                        dcc.Input(id={'type': 'blu-input',        #3
                                      'index': index},
                                  type='number',
                                  min=0,
                                  max=255,
                                  value=255),
                        ]),
                    ]),
                html.Div(className='row', children = [                  #3
                  html.Div(className='six columns', children=[        #0
                    html.H3('Starting Orbit'),                      #0
                    html.Label('Starting Body'),                    #1
                    dcc.Dropdown(id={'type': 'refBody-dropdown',    #2
                                     'index': index},
                        options = name_options(system),
                        value = primName,
                        ),
                    html.Label('Semi-major axis (m)'),              #3
                    dcc.Input(id={'type': 'sma-input',              #4
                                  'index': index},
                              type='number',
                              value = a),
                    html.Label('Eccentricity'),                     #5
                    dcc.Input(id={'type': 'ecc-input',              #6
                                  'index': index},
                              type='number',
                              value = ecc),
                    html.Label('Inclination (°)'),                  #7
                    dcc.Input(id={'type': 'inc-input',              #8
                                  'index': index},
                              type='number',
                              value = inc),
                    html.Label('Argument of the Periapsis (°)'),    #9
                    dcc.Input(id={'type': 'argp-input',            #10
                                  'index': index},
                              type='number',
                              value = argp),
                    html.Label('Longitude of the Ascending Node (°)'),
                                                                   #11
                    dcc.Input(id={'type': 'lan-input',             #12
                                  'index': index},
                              type='number',
                              value = lan),
                    html.Label('Mean anomaly at epoch (radians)'), #13
                    dcc.Input(id={'type': 'mo-input',              #14
                                  'index': index},
                              type='number',
                              value = mo),
                    html.Label('Epoch (s)'),                       #15
                    dcc.Input(id={'type': 'epc-input',             #16
                                  'index': index},
                              type='number',
                              value = epoch),
                    ]),
                html.Div(className='six columns', children=[         #1
                    html.H3('Maneuver Nodes'),                     #0
                    html.Label('Number of maneuver nodes'),        #1
                    dcc.Input(id={'type': 'numNodes-input',        #2
                                  'index': index},
                              type = 'number',
                              value = numNodes,
                              min = 0,
                              step = 1),
                    html.Div(id={'type': 'nodes-div',              #3
                                 'index': index},
                             children=[]
                        ),
                    ]),
                  ]),
                ])
    
    for ii in range(numNodes):
        add_maneuver_node(newTab.children[3].children[1].children[3].children, ii+1, maneuverNodes[ii])
    
    return newTab

def make_new_graphs_tab(sys, idx, sliderStartTime, sliderEndTime):
    
    blankFig = blank_plot()
    
    tab = dcc.Tab(
                    id={'type': 'systemGraph-tab',
                                'index': idx},
                    label=str(sys)+' system',
                    className='control-tab',
                    value=str(sys),
                    children=[
                        dcc.Graph(
                            id={'type': 'system-graph',
                                'index': idx},
                            figure=blankFig
                            ),
                        dcc.Graph(
                            id={'type': 'surface-graph',
                                'index': idx},
                            figure=blankFig,
                            style={'display': 'none'}
                            ),
                        html.Label('Universal Time (s)'),
                        dcc.Input(
                            id={'type': 'plotTime-input',
                                'index': idx},
                            type='number',
                            ),
                        dcc.Slider(
                            id={'type': 'plotTime-slider',
                                'index': idx},
                            min=round(sliderStartTime)+1,
                            max=round(sliderEndTime)-1,
                            step=1,
                            value = round(sliderStartTime)+1,
                            marks = dict(),
                            included=False,
                            updatemode='mouseup'
                            ),
                        html.A(children=html.Button('Download Orbit Plot'),
                            id={'type': 'orbitDownload-button',
                                'index': idx},
                            download=str(sys)+'_system'+'.html',
                            target="_blank"
                            ),
                        html.A(children=html.Button('Download Surface Projection'),
                            id={'type': 'surfaceDownload-button',
                                'index': idx},
                            download=str(sys)+'_system'+'.html',
                            target="_blank",
                            ),
                        html.Div(
                            id={'type': 'tab-orb-rendered',
                                'index': idx},
                            children = [False]
                            ),
                        html.Div(
                            id={'type': 'tab-surf-rendered',
                                'index': idx},
                            children = [False]
                            )
                        ]
                    )
    return tab

def make_surface_projection_plot(orbitsTimes, startTime, endTime,
                                 numSurfaceRevsBefore, numSurfaceRevsAfter,
                                 surfaceMapType, displays):
    
    if 'surfProj' in displays:
        surfStyle = None
        fig = dash.no_update
    else:
        surfStyle = {'display': 'none'}
        fig = go.Figure()
    
    return fig
#%% download functions

@app.server.route('/download/<path:path>')
def serve_static(path):
    return send_from_directory(DOWNLOAD_DIRECTORY, path, as_attachment=True)

#%% app layout

app.layout = html.Div(id='kspti-body', children = [
  html.Div(id='header', className='row', style={'background-image': 'linear-gradient(#003236, #1E1E1E)'}, children=[
      html.Div(className='six columns', children =[
          html.H1("   KSP Trajectory Illustrator",
                  style={"white-space": "pre",
                         'float' : 'left',
                         'position' : 'relative',
                         'padding-top' : 50,
                         'padding-right' : 25
                    }),
          ]),
      html.Div(className='two columns', children = [
          html.A([
            html.Img(
                src=app.get_asset_url("KSP forum logo.png"),
                style={
                    'float' : 'left',
                    'position' : 'relative',
                    'padding-top' : 50,
                    'padding-right' : 0
                })
            ], href='https://forum.kerbalspaceprogram.com/index.php?/topic/195405-web-ksp-transfer-illustrator/')
          ]),
      html.Div(className='two columns', children = [
          html.A([
            html.Img(
                src=app.get_asset_url("Github logo.png"),
                style={
                    'float' : 'left',
                    'position' : 'relative',
                    'padding-top' : 25,
                    'padding-right' : 100
                })
            ], href='https://github.com/theastrogoth/KSP-Transfer-Illustrator')
          ]),
      html.Div(className='two columns', children =[
          html.Img(
              src=app.get_asset_url("logo.png"),
              style={
                    'float' : 'left',
                    'position' : 'relative',
                    'padding-top' : 0,
                    'padding-right' : 25
                })
          ]),
      ]),
  
  html.Div(className='row', children=[
    html.Div(className='four columns', children=[
        dcc.Tabs(id='kspti-control-tabs', className='control-tabs', value='craft', children=[
            dcc.Tab(className='control-tab', label='Craft Settings', value='craft', children=[
                html.H3('Craft Settings'),
                html.Label('Number of crafts'),
                dcc.Input(id = 'numCrafts-input',  
                          type='number',
                          value = 0,
                          min = 0,
                          step = 1),
                html.Label('Number of revolutions to search for intercept'),
                dcc.Input(id = 'numRevs-input',  
                          type='number',
                          value = 5,
                          min = 0,
                          step = 1),
                html.H3('Load from .sfs File'),
                dcc.Upload(
                    id='persistenceFile-upload',
                    children=html.Div([
                        'Drag and Drop or ',
                        html.A('Select Files')
                    ]),
                    style={
                        'width': '100%',
                        'height': '60px',
                        'lineHeight': '60px',
                        'borderWidth': '1px',
                        'borderStyle': 'dashed',
                        'borderRadius': '5px',
                        'textAlign': 'center',
                        'margin': '10px'
                        },
                    multiple=False
                    ),
                html.Label('Select craft/object to add:'),
                dcc.Dropdown(
                    id='persistenceCraft-dropdown',
                    ),
                html.Button(children = 'Add Craft',
                            className = 'button-primary',
                            id = 'addPersistenceCraft-button',
                            n_clicks = 0
                    ),
                ]),
            dcc.Tab(label='System Settings', className='control-tab', value='system', children=[
                html.H3('System Settings'),
                html.Label('System'),
                dcc.RadioItems(
                    id = 'system-radio',
                    options=[
                        {'label': 'Kerbol (Stock)', 'value': 'stock'},
                        {'label': 'Kerbol (Outer Planets Mod)', 'value': 'opm'},
                        {'label': 'Sol (Real Solar System)', 'value': 'rss'},
                        {'label': 'Uploaded System', 'value': 'upload'}],
                    value='stock',
                    ),
                html.H3('System Resizing/Rescaling'),
                html.Label('System Resize Factor'),
                dcc.Input(id = 'systemResize-input',  
                          type='number',
                          value = 1,
                          min = 0),
                html.Label('System Rescale Factor'),
                dcc.Input(id = 'systemRescale-input',
                          type='number',
                          value = 1,
                          min = 0),
                html.Label('Day Length Multiplier'),
                dcc.Input(id='systemDayScale-input',
                          type='number',
                          value = 1,
                          min = 0),
                html.H3('Load System from .ini File'),
                dcc.Upload(
                    id='systemFile-upload',
                    children=html.Div([
                        'Drag and Drop or ',
                        html.A('Select Files')
                    ]),
                    style={
                        'width': '100%',
                        'height': '60px',
                        'lineHeight': '60px',
                        'borderWidth': '1px',
                        'borderStyle': 'dashed',
                        'borderRadius': '5px',
                        'textAlign': 'center',
                        'margin': '10px'
                        },
                    multiple=False
                    ),
                ]),
            dcc.Tab(label='Time Settings', className='control-tab', value='time', children=[
                html.H3('Time Settings'),
                html.Label('Date Format'),
                dcc.RadioItems(
                    id = 'dateFormat-radio',
                    options=[
                        {'label': 'Kerbin Time (6h days, 426d years)',
                         'value': 'Kerbin'},
                        {'label': 'Earth Time (24h days, 365d years)',
                         'value': 'Earth'},
                        ],
                    value='Kerbin'
                    ),
                html.H3('Plot Time Limits'),
                html.Label('Start time (s)'),
                dcc.Input(id = 'startTime-input',  
                          type='number',
                          min = 0),
                html.Label('End time (s)'),
                dcc.Input(id = 'endTime-input',  
                          type='number'),
                html.H3('Surface Projection Options'),
                html.Label('Max number of revolutions plotted before selected time'),
                dcc.Input(id='numSurfaceRevsBefore-input',
                          type='number',
                          min = 0,
                          value = 0),
                html.Label('Max number of revolutions plotted after selected time'),
                dcc.Input(id='numSurfaceRevsAfter-input',
                          type='number',
                          min = 0,
                          value = 3),
                ]),
            dcc.Tab(label='Display Settings', className='control-tab', value='display', children=[
                html.H3('Orbit Plot Display'),
                html.Label('Planet Texture'),
                dcc.RadioItems(
                    id = 'surfaceTexture-radio',
                    options=[
                        {'label': 'Solid Color',
                         'value': 'Solid'},
                        {'label': 'Color Map',
                         'value': 'Color'},
                        {'label': 'Biome Map',
                         'value': 'Biome'},
                        {'label': 'Height Map',
                         'value': 'Height'},
                        ],
                    value='Solid'
                    ),
                html.H3('Surface Projection Display'),
                html.Label('Surface Projection Background'),
                dcc.RadioItems(
                    id = 'surfaceMap-radio',
                    options=[
                        {'label': 'Blank',
                         'value': 'Blank'},
                        {'label': 'Color Map',
                         'value': 'Color'},
                        {'label': 'Biome Map',
                         'value': 'Biome'},
                        {'label': 'Height Map',
                         'value': 'Height'},
                        ],
                    value='Blank'
                    ),
                ])
            ]),
        ]),
    
    html.Div(className='four columns', children=[
        html.Div(
            html.Button(children = 'Add New Craft',
                        className = 'button-primary',
                        id = 'addCraft-button',
                        n_clicks = 0
                ),
            ),
        dcc.Tabs(id='craft-tabs', style={'padding-top' : 48}, className='control-tabs', value='Craft 1', children=[
            # make_new_craft_tab('Craft 1', 1, kerbol_system,
            #                     'Kerbin', 700000,0,0,0,0,0,4510000,
            #                     [[1054.39,0,0,4519600.550],
            #                      [0,7.03,0,7019695.568],
            #                      [-653.34,5.86,0,10867800]]),
            # make_new_craft_tab('Craft 1', 1, kerbol_system)
            ]),
        ]),
    
    
    html.Div(className='four columns', children=[
        html.Div(
            html.Button(children = 'Plot!',
                        className = 'button-primary',
                        id = 'plot-button',
                        n_clicks = 0
                ),
            ),
        dcc.Checklist(
            id = 'display-checklist',
            value = ['orbits', '3dSurfs', 'SoIs', 'arrows'],
            options=[
                {'label': 'Orbits', 'value': 'orbits'},
                {'label': 'Body Surfaces', 'value': '3dSurfs'},
                {'label': 'Spheres of Influence', 'value': 'SoIs'},
                {'label': 'Burn Arrows', 'value': 'arrows'},
                {'label': 'Apses', 'value': 'apses'},
                {'label': 'Nodes', 'value': 'nodes'},
                {'label': 'Reference Direction', 'value': 'ref'},
                {'label': 'Surface Projection Plot', 'value': 'surfProj'}
                ],
            labelStyle={'display': 'inline-block'},
            ),
        dcc.Loading(type='circle', children=[
            dcc.Tabs(id='graph-tabs', className='control-tabs', value='blank', children=[
                dcc.Tab(label='Plots will be generated here', className='control-tab', value='blank', children=[
                    dcc.Graph(
                        id='blank',
                        figure = blank_plot(),
                        )
                    ])
                ])
            ])
        ]),
    # hidden containers
    html.Div(id='orbits-div', style = {'display': 'none'}),
    html.Div(id='dateFormat-div', style = {'display': 'none'}),
    html.Div(id='originalSystems-div', style = {'display': 'none'},
             children=[
                 jsonpickle.encode(kerbol_system),
                 jsonpickle.encode(sol_system)]),
    html.Div(id='allSystems-div', style = {'display': 'none'},
             children=[
                 jsonpickle.encode(kerbol_system),
                 jsonpickle.encode(outer_planets_system),
                 jsonpickle.encode(sol_system),
                 jsonpickle.encode(kerbol_system)]),
    html.Div(id='system-div', style={'display': 'none',}, 
             children=jsonpickle.encode(kerbol_system)),
    html.Div(id='orbitStartTimes-div', style={'display': 'none'},
             children=[]),
    html.Div(id='orbitEndTimes-div', style={'display': 'none'},
             children=[]),
    html.Div(id='plotSystems-div', style={'display': 'none'},
             children=[]),
    html.Div(id='systemStartTimes-div', style={'display': 'none'},
             children=[]),
    html.Div(id='systemEndTimes-div', style={'display': 'none'},
             children=[]),
    html.Div(id='numCrafts-div', style={'display': 'none'},
             children=[0]),
    html.Div(id='persistenceCrafts-div', style={'display': 'none'},
             children=[]),
    ])
  ])

#%% callbacks
@app.callback(
     Output('dateFormat-div', 'children'),
    [Input('dateFormat-radio', 'value'),
     Input('systemResize-input', 'value'),
     Input('systemRescale-input','value'),
     Input('systemDayScale-input','value')]
    )
def set_date_format(selected_format, resizeFactor, rescaleFactor, dayFactor):
    formats = dict(Kerbin = dict(day=6, year=426),
                   Earth = dict(day=24, year=365))
    
    dateFormat = formats[selected_format]
    day = dateFormat['day']
    year = dateFormat['year']
    
    day = day * dayFactor
    
    aScale = rescaleFactor
    muScale = resizeFactor**2
    year = year * math.sqrt(aScale**3/muScale) / dayFactor
    
    year = round(year)
    day = round(day)
    
    return dict(day=day, year=year)

@app.callback(
    [Output('allSystems-div','children'),
     Output('system-radio','value')],
    [Input('systemFile-upload','contents')],
    [State('allSystems-div','children'),
     State('system-radio','options')],
    prevent_initial_call = True
    )
def add_system_from_ini(iniFile, allSystems, radioOptions):
    if iniFile is None:
        return dash.no_update, dash.no_update
    
    iniFile = iniFile.split(',')[1]
    iniFile = b64decode(iniFile).decode('utf-8')
    newSystem = ini_to_system(iniFile, False)
    
    allSystems[3] = jsonpickle.encode(newSystem)
    
    return allSystems, 'upload'

@app.callback(
     Output('system-div', 'children'),
    [Input('system-radio','value'),
     Input('systemResize-input','value'),
     Input('systemRescale-input','value'),
     Input('allSystems-div', 'children')]
    )
def set_system(system_name, resizeFactor, rescaleFactor, all_systems):
    if system_name == 'stock':
        system = jsonpickle.decode(all_systems[0])
    elif system_name == 'opm':
        system = jsonpickle.decode(all_systems[1])
    elif system_name == 'rss':
        system = jsonpickle.decode(all_systems[2])
    elif system_name == 'upload':
        system = jsonpickle.decode(all_systems[3])
    else:
        return dash.no_update
    
    for body in system:
        body.resize(resizeFactor)
        body.rescale(rescaleFactor)
    
    return jsonpickle.encode(system)

@app.callback(
     Output('numCrafts-div','children'),
    [Input('numCrafts-input', 'value')],
    [State('numCrafts-div','children')]
    )
def update_num_crafts(numCrafts, prevNumCrafts):
    if numCrafts == prevNumCrafts:
        return dash.no_update
    else:
        return numCrafts

@app.callback(
     Output({'type': 'refBody-dropdown', 'index': MATCH}, 'options'),
    [Input('system-div', 'children')]
    )
def update_ref_body_dropdown(system):
    system = jsonpickle.decode(system)
    return name_options(system)

@app.callback(
     Output({'type': 'craft-tab', 'index': MATCH}, 'label'),
    [Input({'type': 'name-input', 'index': MATCH}, 'value')]
    )
def update_craft_name(name):
    return name

@app.callback(
     Output({'type': 'nodes-div', 'index': MATCH}, 'children'),
    [Input({'type': 'numNodes-input', 'index': MATCH}, 'value')],
    [State({'type': 'nodes-div', 'index': MATCH}, 'children')]
    )
def update_num_nodes(numNodes, prevNodesChildren):
    try:
        prevNumNodes = int(len(prevNodesChildren)/5)
    except:
        prevNumNodes = 0
    if numNodes < prevNumNodes:
        newChildren = prevNodesChildren[0:5*(numNodes)]
    elif numNodes > prevNumNodes:
        newChildren = prevNodesChildren
        for ii in range(numNodes-prevNumNodes):
            add_maneuver_node(newChildren, ii+prevNumNodes+1)
    else:
        return dash.no_update
    
    return newChildren

@app.callback(
    [Output('craft-tabs','children'),
     Output('craft-tabs','value'),
     Output('numCrafts-input','value')],
    [Input('numCrafts-div','children'),
     Input('addPersistenceCraft-button','n_clicks'),
     Input('addCraft-button','n_clicks'),
     Input({'type': 'deleteCraft-button', 'index': ALL}, 'n_clicks')],
    [State('craft-tabs','children'),
     State('craft-tabs','value'),
     State('system-div','children'),
     State('persistenceCraft-dropdown','value'),
     State('persistenceCrafts-div','children')],
    prevent_initial_call=True
    )
def update_craft_tabs(numCrafts,
                       addFileCraftClicks, addCraftClicks, delCraftClicks,
                       prevCraftTabs, prevTabVal, system,
                       addCraftName, persistenceCrafts):
    
    system = jsonpickle.decode(system)
    prevNumCrafts = len(prevCraftTabs)
    
    tabIdxs = []
    for ii, tab in enumerate(prevCraftTabs):
            tabIdxs.append(tab['props']['children'][0]['props']['children'][0]['props']['id']['index'])
    
    ctx = dash.callback_context
    if ctx.triggered[0]['prop_id'].split('.')[0] == 'addPersistenceCraft-button':
        persistenceCrafts = jsonpickle.decode(persistenceCrafts)
        craft = [vs for vs in persistenceCrafts if vs.name == addCraftName][0]
        
        craftTabs = prevCraftTabs
        tabValues = [tab['props']['value'] for tab in craftTabs]
        if not craft.name in tabValues:
            craftTabs.append(
                make_new_craft_tab(craft.name, prevNumCrafts+1, system,
                                    craft.orb.prim.name, craft.orb.a, 
                                    craft.orb.ecc, craft.orb.inc, 
                                    craft.orb.argp, craft.orb.lan,
                                    craft.orb.mo, craft.orb.epoch,
                                    craft.maneuverNodes)
                )
            numCrafts = numCrafts+1
            tabVal = craft.name
        else:
            tabVal = prevTabVal
    
    elif 'deleteCraft-button' in ctx.triggered[0]['prop_id']:
        craftTabs = prevCraftTabs
        idx = int(str(ctx.triggered[0]['prop_id']).split('.')[0][9])
        for ii, tIdx in enumerate(tabIdxs):
            if tIdx == idx:
                tabIdx = ii
                break
        if prevNumCrafts == 1:
            tabVal = None
        elif tabIdx == 0:
            tabVal = craftTabs[1]['props']['value']
        else:
            tabVal = craftTabs[tabIdx-1]['props']['value']
        del(craftTabs[tabIdx])
        numCrafts = numCrafts-1
    
    elif numCrafts < prevNumCrafts:
        craftTabs = prevCraftTabs[0:numCrafts]
        try:
            tabVal = craftTabs[-1]['props']['value']
        except IndexError:
            tabVal = None
    elif (numCrafts > prevNumCrafts) or ('addCraft-button' in ctx.triggered[0]['prop_id']):
        if numCrafts==prevNumCrafts:
            numCrafts = numCrafts+1
        craftTabs = prevCraftTabs
        newIdx = 1
        for jj in range(numCrafts-prevNumCrafts):
            while newIdx in tabIdxs:
                newIdx = newIdx+1
            craftTabs.append(
                make_new_craft_tab('Craft '+str(newIdx),                  \
                                    newIdx, system)
                  )
            tabVal = 'Craft '+str(newIdx)
            tabIdxs.append(newIdx)
        tabOrder = np.argsort(tabIdxs)
        newCraftTabs = []
        for ii in tabOrder:
            newCraftTabs.append(craftTabs[ii])
        craftTabs = newCraftTabs
        
    else:
        craftTabs = prevCraftTabs
        tabVal = prevTabVal
    
    return craftTabs, tabVal, numCrafts

@app.callback(
    [Output('orbits-div','children'),
     Output('orbitStartTimes-div','children'),
     Output('orbitEndTimes-div','children'),
     Output('plotSystems-div','children'),
     Output('systemStartTimes-div','children'),
     Output('systemEndTimes-div','children')],
    [Input('plot-button','n_clicks')],
    [State('system-div','children'),
     State('craft-tabs','children'),
     State('numRevs-input','value'),
     State('startTime-input','value'),
     State('endTime-input','value')]
    )
def update_orbits(nClicks, system, craftTabs, numRevs, startTime, endTime):
    
    # don't update on page load
    if nClicks == 0:
        return dash.no_update
    
    craftOrbits = []
    craftTimes = []
    systems = []
    sliderStartTimes = []
    sliderEndTimes = []
    orbitStartTimes = []
    orbitEndTimes = []
    
    for tab in craftTabs:
        
        # get parameters from tab children
        startBodyName = tab['props']['children'][3]['props']['children'][0]['props']['children'][2]['props']['value']
        startA = tab['props']['children'][3]['props']['children'][0]['props']['children'][4]['props']['value']
        startEcc = tab['props']['children'][3]['props']['children'][0]['props']['children'][6]['props']['value']
        startInc = tab['props']['children'][3]['props']['children'][0]['props']['children'][8]['props']['value']
        startArgP = tab['props']['children'][3]['props']['children'][0]['props']['children'][10]['props']['value']
        startLAN = tab['props']['children'][3]['props']['children'][0]['props']['children'][12]['props']['value']
        startMo = tab['props']['children'][3]['props']['children'][0]['props']['children'][14]['props']['value']
        startEpoch = tab['props']['children'][3]['props']['children'][0]['props']['children'][16]['props']['value']
        
        nodesChildren = tab['props']['children'][3]['props']['children'][1]['props']['children'][3]['props']['children']
        
        # prepare system information, start body
        if not isinstance(system, list):
            system = jsonpickle.decode(system)
        sBody = [x for x in system if x.name == startBodyName][0]
        
        # prepare start and end orbit parameters
        if startA is None:
            startA = sBody.eqr + 100000
        if startEcc is None:
            startEcc = 0
        if startInc is None:
            startInc = 0
        if startArgP is None:
            startArgP = 0
        if startLAN is None:
            startLAN = 0
        if startMo is None:
            startMo = 0
        if startEpoch is None:
            startEpoch = 0
        
        sOrb = Orbit(startA, startEcc, startInc*math.pi/180, startArgP*math.pi/180,
                     startLAN*math.pi/180, startMo, startEpoch, sBody)
        
        # prepare maneuver nodes
        nodeBurns = []
        nodeTimes = []
        for ii in range(int(len(nodesChildren)/5)):
            nodeBurns.append([nodesChildren[5*ii+1]["props"]["value"],
                              nodesChildren[5*ii+2]["props"]["value"],
                              nodesChildren[5*ii+3]["props"]["value"],
                              ])
            nodeTimes.append(nodesChildren[5*ii+4]['props']['value'])
        
        # set starting orbit and time
        orbits = [sOrb]
        if startTime is None:
            if len(nodeTimes)==0:
                times = [startEpoch]
            else:
                times = [np.amin(nodeTimes) - sOrb.get_period()]
        else:
            if not len(nodeTimes)==0:
                if np.amin(nodeTimes) < startTime:
                    times = [np.amin(nodeTimes)]
                else:
                    times = [startTime]
            else:
                times = [startTime]
        
        # propagate orbit and apply maneuver nodes
        nodeIdx = 0
        stopSearch = False
        while not stopSearch:
            t = times[-1]
            nextOrb, time = orbits[-1].propagate(t+0.1)
            # try future revolutions if no new escape/encounter in first rev
            if nextOrb is None and orbits[-1].ecc<1:
                for ii in range(numRevs):
                    t = t + orbits[-1].get_period()
                    nextOrb, time = orbits[-1].propagate(t+0.1)
                    if not nextOrb is None:
                        break
            
            # if no escape/encounter, apply next maneuver node
            if nextOrb is None:
                if nodeIdx < len(nodeTimes):
                    time = nodeTimes[nodeIdx]
                    pos, vel = orbits[-1].get_state_vector(time)
                    burn = burn_components_to_absolute(nodeBurns[nodeIdx][0],
                                                       nodeBurns[nodeIdx][1],
                                                       nodeBurns[nodeIdx][2],
                                                       pos, vel)
                    nextOrb = Orbit.from_state_vector(pos, vel+burn, time,  \
                                                      orbits[-1].prim);
                    orbits.append(nextOrb)
                    times.append(time)
                    nodeIdx = nodeIdx+1
            
            # otherwise, check if a maneuver happens before escape/encounter
            else:
                t = time
                if nodeIdx < len(nodeTimes):
                    if t > nodeTimes[nodeIdx]:
                        time = nodeTimes[nodeIdx]
                        pos, vel = orbits[-1].get_state_vector(time)
                        burn = burn_components_to_absolute(nodeBurns[nodeIdx][0],
                                                           nodeBurns[nodeIdx][1],
                                                           nodeBurns[nodeIdx][2],
                                                           pos, vel)
                        nextOrb = Orbit.from_state_vector(pos, vel+burn, time,  \
                                                          orbits[-1].prim);
                        orbits.append(nextOrb)
                        times.append(time)
                        nodeIdx = nodeIdx+1
                    else:
                        orbits.append(nextOrb)
                        times.append(time)
                else:
                    orbits.append(nextOrb)
                    times.append(time)
            
            if not endTime is None:
                if t > endTime:
                    stopSearch = True
            
            # end search if no maneuvers left and no escape/encounter found
            if (nextOrb is None and nodeIdx >= len(nodeTimes)):
                stopSearch = True
        
        craftOrbits.append(orbits)
        craftTimes.append(times)
        
        # determine start and end times for plotting in each system
        sTimes = []
        eTimes = []
        print(times)
        for ii in range(len(orbits)):
            
            orb = orbits[ii]
            sTime = times[ii]
            soi = orb.prim.soi
            
            if ii==0 or sTime < times[0]:
                sTime = times[0]
            
            if ii == len(orbits)-1:
                eTime = eTime + orb.get_period()
            else:
                eTime = times[ii+1]
            
            if not endTime is None:
                if ii == len(orbits)-1 or endTime < eTime:
                    eTime = endTime
                    
            
            if orb.prim.name in systems:
                figIdx = systems.index(orb.prim.name)
                if sTime < sliderStartTimes[figIdx]:
                    sliderStartTimes[figIdx] = sTime
                if eTime > sliderEndTimes[figIdx]:
                    sliderEndTimes[figIdx] = eTime
            else:
                systems.append(orb.prim.name)
                sliderStartTimes.append(sTime)
                sliderEndTimes.append(eTime)
                figIdx = -1
            
            # save start and end times for each orbit
            sTimes.append(sTime)
            eTimes.append(eTime)
            
            if not endTime is None:
                if eTime >= endTime:
                    break
        
        orbitStartTimes.append(sTimes)
        orbitEndTimes.append(eTimes)
    
    return jsonpickle.encode(craftOrbits), orbitStartTimes, orbitEndTimes,  \
           systems, sliderStartTimes, sliderEndTimes

@app.callback(
    [Output('graph-tabs','children'),
     Output('graph-tabs', 'value')],
    [Input('plotSystems-div','children')],
    [State('systemStartTimes-div','children'),
     State('systemEndTimes-div','children')]
    )
def update_graph_tabs(systems, sliderStartTimes, sliderEndTimes):
    
    blankFig = blank_plot(),
    
    tabs=[]
    for idx, sys in enumerate(systems):
        
        if sys == 'Sun':
            systems[idx] = 'Solar'
        
        tabs.append(make_new_graphs_tab(systems[idx], idx,                  \
                                        sliderStartTimes[idx],              \
                                        sliderEndTimes[idx]))
        
    tabVal = systems[0]
    return tabs, tabVal

@app.callback(
    [Output({'type': 'system-graph', 'index': MATCH}, 'figure'),
     Output({'type': 'orbitDownload-button', 'index': MATCH}, 'href'),
     Output({'type': 'tab-orb-rendered', 'index': MATCH}, 'children')],
    [Input('graph-tabs', 'value'),
     Input({'type': 'plotTime-slider', 'index': MATCH}, 'value'),
     Input('display-checklist','value'),
     Input('dateFormat-div','children'),
     Input('surfaceTexture-radio', 'value')],
    [State('startTime-input', 'value'),
     State('endTime-input', 'value'),
     State('orbits-div','children'),
     State('orbitStartTimes-div','children'),
     State('orbitEndTimes-div', 'children'),
     State('plotSystems-div', 'children'),
     State('craft-tabs', 'children'),
     State('system-div', 'children'),
     State({'type': 'tab-orb-rendered', 'index': MATCH}, 'children')]
    )
def update_orbit_graph(systemName, sliderTime, displays, dateFormat,
                       surfaceTextureType, 
                       startTime, endTime,
                       orbitsTimes, orbitStartTimes, orbitEndTimes,
                       plotSystems, craftTabs, system,
                       orbRendered):
    
    ctx = dash.callback_context
    tabTrigger = ctx.triggered[0]['prop_id'].split('.')[0] == 'graph-tabs'
    
    figIdx = ctx.inputs_list[1]['id']['index']
    craftOrbits = jsonpickle.decode(orbitsTimes)
    system = jsonpickle.decode(system)
    
    primaryName = plotSystems[figIdx]
    if systemName == 'Solar':
        systemName = 'Sun'
    
    if (not primaryName == systemName) or (orbRendered[0] and tabTrigger):
        return dash.no_update, dash.no_update, dash.no_update
    
    primaryBody = [x for x in system if x.name == primaryName][0]
    
    fig = go.Figure()
    lim = plot_system(fig, primaryBody, sliderTime,                         \
                      dateFormat, displays, surfaceTextureType);
    set_trajectory_plot_layout(fig, lim, uirev = primaryBody.name)
    
    for nn in range(len(craftOrbits)):
        
        craftName = craftTabs[nn]['props']['label']
        
        # prepare color
        color = (                                                           \
            craftTabs[nn]['props']['children'][2]['props']['children'][1]['props']['children'][1]['props']['value'],
            craftTabs[nn]['props']['children'][2]['props']['children'][1]['props']['children'][2]['props']['value'],
            craftTabs[nn]['props']['children'][2]['props']['children'][1]['props']['children'][3]['props']['value']
                )
        
        # prepare maneuver nodes
        nodesChildren = craftTabs[nn]['props']['children'][3]['props']['children'][1]['props']['children'][3]['props']['children']
        nodeBurns = []
        nodeTimes = []
        for kk in range(int(len(nodesChildren)/5)):
            nodeBurns.append([nodesChildren[5*kk+1]["props"]["value"],
                              nodesChildren[5*kk+2]["props"]["value"],
                              nodesChildren[5*kk+3]["props"]["value"],
                              ])
            nodeTimes.append(nodesChildren[5*kk+4]['props']['value'])
        
        orbits = craftOrbits[nn]
        sTimes = orbitStartTimes[nn]
        eTimes = orbitEndTimes[nn]
        
        for ii in range(len(sTimes)):
            orb = orbits[ii]
            sTime = sTimes[ii]
            eTime = eTimes[ii]
            
            if not ((sTime is None) or (eTime is None)) and                 \
               orb.prim.name==primaryBody.name:
                
                if not startTime is None:
                    if eTime < startTime:
                        continue
                    elif sTime < startTime:
                        sTime = startTime
                
                # draw orbits
                if 'orbits' in displays:
                    add_orbit(fig, orb, sTime, eTime, 201,
                          dateFormat, 'apses' in displays, 'nodes' in displays,
                          fullPeriod=False, color=color, name=craftName,
                          style='solid', fade=True)
                
                # add burn arrows
                if (eTime in nodeTimes) and ('arrows' in displays):
                    burnIdx = nodeTimes.index(eTime)
                    burnDV = nodeBurns[burnIdx]
                    add_burn_arrow(fig, burnDV, eTime, orb, dateFormat,
                                   1/2, 'Burn'+str(burnIdx+1), color, False)
                
                # add craft marker
                if (sTime<=sliderTime) and ((sliderTime<eTime) or ((ii==len(orbits)-1) and (orb.ecc<1))):
                    craft = Body('Craft'+str(nn+1),0,0,0,orb=orb,color=color)
                    add_body(fig, craft, sliderTime, False, size = 4, symbol = 'square')
    
    # create downloadable HTML file of orbit plot
    orbitFilename = plotSystems[figIdx]+'_system.html'
    orbitPath = os.path.join(DOWNLOAD_DIRECTORY, orbitFilename)
    orbitLocation = "/download/{}".format(urlquote(orbitFilename))
    fig.write_html(orbitPath)
    
    return fig, orbitLocation, [True]

@app.callback(
    [Output({'type': 'surface-graph', 'index': MATCH}, 'figure'),
     Output({'type': 'surface-graph', 'index': MATCH}, 'style'),
     Output({'type': 'surfaceDownload-button', 'index': MATCH}, 'href'),
     Output({'type': 'surfaceDownload-button', 'index': MATCH}, 'style'),
     Output({'type': 'tab-surf-rendered', 'index': MATCH}, 'children')],
    [Input('graph-tabs', 'value'),
     Input({'type': 'plotTime-slider', 'index': MATCH}, 'value'),
     Input('display-checklist','value'),
     Input('dateFormat-div','children'),
     Input('numSurfaceRevsBefore-input','value'),
     Input('numSurfaceRevsAfter-input','value'),
     Input('surfaceMap-radio', 'value')],
    [State('startTime-input', 'value'),
     State('endTime-input', 'value'),
     State('orbits-div','children'),
     State('orbitStartTimes-div','children'),
     State('orbitEndTimes-div', 'children'),
     State('plotSystems-div', 'children'),
     State('craft-tabs', 'children'),
     State('system-div', 'children'),
     State({'type': 'tab-surf-rendered', 'index': MATCH}, 'children')]
    )
def update_surface_graph(systemName, sliderTime, displays, dateFormat,
                       numSurfaceRevsBefore, numSurfaceRevsAfter,
                       surfaceMapType,
                       startTime, endTime,
                       orbitsTimes, orbitStartTimes, orbitEndTimes,
                       plotSystems, craftTabs, system,
                       surfRendered):
    
    ctx = dash.callback_context
    tabTrigger = ctx.triggered[0]['prop_id'].split('.')[0] == 'graph-tabs'
    checkTrigger = ctx.triggered[0]['prop_id'].split('.')[0] == 'display-checklist'
    
    figIdx = ctx.inputs_list[1]['id']['index']
    craftOrbits = jsonpickle.decode(orbitsTimes)
    system = jsonpickle.decode(system)
    
    primaryName = plotSystems[figIdx]
    if systemName == 'Solar':
        systemName = 'Sun'
    
    if 'surfProj' in displays:
        surfStyle = None
        hidden = False
    else:
        surfStyle = {'display': 'none'}
        hidden = True
    
    # Don't do anything if another tab is selected
    if not (primaryName == systemName):
        # print('   tab not selected')
        return dash.no_update, dash.no_update, dash.no_update,              \
               dash.no_update, dash.no_update;
    
    # Need to render again next time if it is hidden when the slider changes
    # or other inputs change
    if hidden and (not (tabTrigger or checkTrigger)):
        # print('   set unrendered')
        return dash.no_update, surfStyle, dash.no_update,              \
               surfStyle, [False];
    
    # No need to rerender if only the tab/checks have changed and already 
    # rendered
    if surfRendered[0] and (tabTrigger or checkTrigger):
        # print('   unchanged')
        return dash.no_update, surfStyle, dash.no_update,              \
               surfStyle, dash.no_update;
    
    # No need to rerender if hidden and only the tab has changed
    if hidden and tabTrigger:
        # print('   unchanged')
        return dash.no_update, surfStyle, dash.no_update,              \
               surfStyle, dash.no_update;
    
    # print('   rerendered')
    primaryBody = [x for x in system if x.name == primaryName][0]
    
    surfFig = go.Figure()
    if surfaceMapType == 'Blank':
        set_surface_projection_layout(surfFig,
                                      mapUrl=None,
                                      uirev = primaryBody.name+'Surf')
    else:
        set_surface_projection_layout(surfFig,
                                      mapUrl=map_url(primaryBody.name, surfaceMapType),
                                      uirev = primaryBody.name+'Surf')
    
    for nn in range(len(craftOrbits)):
        
        craftName = craftTabs[nn]['props']['label']
        
        # prepare color
        color = (                                                           \
            craftTabs[nn]['props']['children'][2]['props']['children'][1]['props']['children'][1]['props']['value'],
            craftTabs[nn]['props']['children'][2]['props']['children'][1]['props']['children'][2]['props']['value'],
            craftTabs[nn]['props']['children'][2]['props']['children'][1]['props']['children'][3]['props']['value']
                )
        
        # prepare maneuver nodes
        nodesChildren = craftTabs[nn]['props']['children'][3]['props']['children'][1]['props']['children'][3]['props']['children']
        nodeBurns = []
        nodeTimes = []
        for kk in range(int(len(nodesChildren)/5)):
            nodeBurns.append([nodesChildren[5*kk+1]["props"]["value"],
                              nodesChildren[5*kk+2]["props"]["value"],
                              nodesChildren[5*kk+3]["props"]["value"],
                              ])
            nodeTimes.append(nodesChildren[5*kk+4]['props']['value'])
        
        orbits = craftOrbits[nn]
        sTimes = orbitStartTimes[nn]
        eTimes = orbitEndTimes[nn]
        
        for ii in range(len(sTimes)):
            orb = orbits[ii]
            sTime = sTimes[ii]
            eTime = eTimes[ii]
            
            if not ((sTime is None) or (eTime is None)) and                 \
               orb.prim.name==primaryBody.name:
                
                if not startTime is None:
                    if eTime < startTime:
                        continue
                    elif sTime < startTime:
                        sTime = startTime
        
                # surface projection
                if surfStyle is None:
                    if numSurfaceRevsBefore is None:
                        numSurfaceRevsBefore = 1
                    if numSurfaceRevsAfter is None:
                        numSurfaceRevsAfter = 1
                    sTimeEarly = sliderTime - numSurfaceRevsBefore*orb.get_period()
                    eTimeLate = sliderTime + numSurfaceRevsAfter*orb.get_period()
                    
                    if range_in_range(sTimeEarly, eTimeLate, startTime, endTime) or \
                       (ii==len(orbits)-1 and sTimeEarly >= eTime):
                        
                        # add more time for surface projection after slider time
                        if ii==len(orbits)-1:
                            eTime = eTimeLate
                        elif eTimeLate > eTime:
                            eTime = eTimeLate
                        
                        if not endTime is None:
                                if eTime > endTime:
                                    eTime = endTime
                        
                        # add more time for surface projection before slider time
                        if ii==0:
                            sTime = sTimeEarly
                        elif sTimeEarly < sTime:
                            sTime = sTimeEarly
                        
                        if not startTime is None:
                            if sTime < startTime:
                                sTime = startTime
                        
                        numPts = math.ceil((eTime-sTime)/orb.get_period()*101)
                        
                        # add surface projection
                        add_orbit_surface_projection(surfFig, orb, sTime, eTime,
                                                      name=craftName+' orbit '+str(ii+1),
                                                      color=color, numPts=numPts)
        
        for ii in range(len(sTimes)):
            orb = orbits[ii]
            sTime = sTimes[ii]
            eTime = eTimes[ii]
            
            if not ((sTime is None) or (eTime is None)) and                 \
               orb.prim.name==primaryBody.name:
            
                # add more time for surface projection if it's the last orbit
                if ii==len(orbits)-1:
                    eTime = sTime + 10*orb.get_period()
                
                # add craft location at slider time
                if (sTime<=sliderTime) and ((sliderTime<eTime) or ((ii==len(orbits)-1) and (orb.ecc<1))):
                    add_orbit_surface_projection(surfFig, orb, sliderTime,
                                                  name=craftName,
                                                  color=color, symbol='square',
                                                  markerSize = 12,
                                                  borderColor='white')
    

    
    # create downloadable HTML file of surface plot
    surfFilename = plotSystems[figIdx]+'_surface.html'
    surfPath = os.path.join(DOWNLOAD_DIRECTORY, surfFilename)
    surfLocation = "/download/{}".format(urlquote(surfFilename))
    surfFig.write_html(surfPath)
    
    return surfFig, surfStyle, surfLocation, surfStyle, [True]

@app.callback(
     Output({'type': 'plotTime-input', 'index': MATCH}, 'value'),
    [Input({'type': 'plotTime-slider', 'index': MATCH}, 'value')],
    [State({'type': 'plotTime-input', 'index': MATCH}, 'value')],
    )
def update_plot_input_time(sliderTime, prevInputTime):
    
    if sliderTime == prevInputTime:
        return dash.no_update
    
    return sliderTime

@app.callback(
     Output({'type': 'plotTime-slider', 'index': MATCH}, 'value'),
    [Input({'type': 'plotTime-input', 'index': MATCH}, 'value')],
    [State({'type': 'plotTime-slider', 'index': MATCH}, 'value')],
    )
def update_plot_slider_time(inputTime, prevSliderTime):
    
    if prevSliderTime == inputTime:
        return dash.no_update
    
    return inputTime

@app.callback(
    [Output('persistenceCrafts-div', 'children'),
     Output('persistenceCraft-dropdown', 'options'),
     Output('persistenceCraft-dropdown', 'value')],
    [Input('persistenceFile-upload', 'contents')],
    [State('system-div', 'children')],
     prevent_initial_call=True
      )
def create_crafts_from_persistence_file(persistenceFile, system):
    
    if persistenceFile is None:
        return dash.no_update, dash.no_update, dash.no_update
    
    system = jsonpickle.decode(system)
    persistenceFile = persistenceFile.split(',')[1]
    persistenceFile = b64decode(persistenceFile).decode('utf-8')
    sfsData = parse_savefile(persistenceFile, False)
    sfsCrafts = sfsData['GAME']['FLIGHTSTATE']['VESSEL']
    crafts = []
    names = []
    for sfsCraft in sfsCrafts:
        
        name = sfsCraft['name']
        while name in names:
            name = name + "x"
        names.append(name)
        
        a = float(sfsCraft['ORBIT']['SMA'])
        ecc = float(sfsCraft['ORBIT']['ECC'])
        inc = float(sfsCraft['ORBIT']['INC'])
        argp = float(sfsCraft['ORBIT']['LPE'])
        lan = float(sfsCraft['ORBIT']['LAN'])
        mo = float(sfsCraft['ORBIT']['MNA'])
        epoch = float(sfsCraft['ORBIT']['EPH'])
        if 'IDENT' in list(sfsCraft['ORBIT'].keys()):
            primName = sfsCraft['ORBIT']['IDENT']
            primName = primName.replace('Squad/','')
            prim = [bd for bd in system if bd.name == primName][0]
        else:
            primRef = float(sfsCraft['ORBIT']['REF'])
            prim = [bd for bd in system if bd.ref == primRef][0]
        
        if not a == 0:
            orb = Orbit(a, ecc, inc, argp, lan, mo, epoch, prim)
        
            try:
                sfsManeuverNodes = sfsCraft['FLIGHTPLAN']['MANEUVER']
            except KeyError:
                sfsManeuverNodes = []
            maneuverNodes = []
            for node in sfsManeuverNodes:
                if isinstance(node, OrderedDict) and len(node)>0:
                    if 'dV' in node.keys() and 'UT' in node.keys():
                        dvStrings = node['dV'].split(',')
                        prograde = float(dvStrings[2])
                        normal = float(dvStrings[1])
                        radial = float(dvStrings[0])
                        time = float(node['UT'])
                        maneuverNodes.append([prograde,normal,radial,time])
            
            crafts.append(Craft(name, orb, maneuverNodes))
    
    craftOptions = name_options(crafts)
    
    return jsonpickle.encode(crafts), craftOptions, crafts[0].name

#%% run app

if __name__ == '__main__':
    app.run_server(debug=False)
