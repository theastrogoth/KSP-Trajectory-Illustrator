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
from base64 import b64decode
from collections import OrderedDict

import jsonpickle
import math
from orbit import Orbit
from body import Body
from vessel import Vessel

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
infile.close
infile = open('outer_planets_system.json','r')
outer_planets_system = jsonpickle.decode(infile.read())
infile.close
infile = open('sol_system.json','r')
sol_system = jsonpickle.decode(infile.read())
infile.close

#%%
def name_options(objectList):
    nameOptions = []
    for ob in objectList:
        nameOptions.append(ob.name) 
    return [{'label': i, 'value': i} for i in nameOptions]

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

def make_new_vessel_tab(label, index, system,
                        primName=None, a=0, ecc=0, inc=0, argp=0, lan=0,
                        mo=0, epoch=0,
                        maneuverNodes=None):
    
    if not maneuverNodes is None:
        numNodes = len(maneuverNodes)
    else:
        numNodes = 0
    
    newTab = dcc.Tab(id = {'type': 'vessel-tab',
                           'index': index},
                    label=label,
                    value=label, 
                    className='control-tab',
                    children=[
                html.Div(style={'padding-top' : 25}, children=[         #0
                    html.Button(children = 'Delete Vessel',
                            className = 'button-primary',
                            id = {'type': 'deleteVessel-button',
                                  'index': index},
                            n_clicks = 0,
                            ),
                    ]),
                html.H3('Plot Style'),                                  #1
                html.Label('Name'),                                     #2
                dcc.Input(id={'type': 'name-input',                     #3
                              'index': index},
                          type='text',
                          value=label),
                html.Label('Color (RGB)'),                              #4
                dcc.Input(id={'type': 'red-input',                      #5
                              'index': index},
                          type='number',
                          min=0,
                          max=255,
                          value=255),
                dcc.Input(id={'type': 'grn-input',                      #6
                              'index': index},
                          type='number',
                          min=0,
                          max=255,
                          value=255),
                dcc.Input(id={'type': 'blu-input',                      #7
                              'index': index},
                          type='number',
                          min=0,
                          max=255,
                          value=255),
                html.H3('Starting Orbit'),                              #8
                html.Label('Starting Body'),                            #9
                dcc.Dropdown(id={'type': 'refBody-dropdown',            #10
                                 'index': index},
                    options = name_options(system),
                    value = primName,
                    ),
                html.Label('Semi-major axis (m)'),                      #11
                dcc.Input(id={'type': 'sma-input',                      #12
                              'index': index},
                          type='number',
                          value = a),
                html.Label('Eccentricity'),                             #13
                dcc.Input(id={'type': 'ecc-input',                      #14
                              'index': index},
                          type='number',
                          value = ecc),
                html.Label('Inclination (°)'),                          #15
                dcc.Input(id={'type': 'inc-input',                      #16
                              'index': index},
                          type='number',
                          value = inc),
                html.Label('Argument of the Periapsis (°)'),            #17
                dcc.Input(id={'type': 'argp-input',                     #18
                              'index': index},
                          type='number',
                          value = argp),
                html.Label('Longitude of the Ascending Node (°)'),      #19
                dcc.Input(id={'type': 'lan-input',                      #20
                              'index': index},
                          type='number',
                          value = lan),
                html.Label('Mean anomaly at epoch (radians)'),          #21
                dcc.Input(id={'type': 'mo-input',                       #22
                              'index': index},
                          type='number',
                          value = mo),
                html.Label('Epoch (s)'),                                #23
                dcc.Input(id={'type': 'epc-input',                      #24
                              'index': index},
                          type='number',
                          value = epoch),
        
                html.H3('Maneuver Nodes'),                              #25
                html.Label('Number of maneuver nodes'),                 #26
                dcc.Input(id={'type': 'numNodes-input',                 #27
                              'index': index},
                          type = 'number',
                          value = numNodes,
                          min = 0,
                          step = 1),
                html.Div(id={'type': 'nodes-div',                      #28
                             'index': index},
                         children=[]
                    ),
                ])
    
    for ii in range(numNodes):
        add_maneuver_node(newTab.children[28].children, ii+1, maneuverNodes[ii])
    
    return newTab


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
                    'float' : 'right',
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
                    'float' : 'right',
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
        html.H3('Settings'),
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
        html.Label('Start time (s)'),
        dcc.Input(id = 'startTime-input',  
                  type='number',
                  min = 0),
        html.Label('End time (s)'),
        dcc.Input(id = 'endTime-input',  
                  type='number'),
        html.Label('Number of revolutions to search for intercept'),
        dcc.Input(id = 'numRevs-input',  
                  type='number',
                  value = 5,
                  min = 0,
                  step = 1),
        html.Label('Number of vessels'),
        dcc.Input(id = 'numVessels-input',  
                  type='number',
                  value = 1,
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
        html.Label('Select vessel/object to add:'),
        dcc.Dropdown(
            id='persistenceVessel-dropdown',
            ),
        html.Button(children = 'Add Vessel',
                    className = 'button-primary',
                    id = 'addPersistenceVessel-button',
                    n_clicks = 0
            ),
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
    
    html.Div(className='four columns', children=[
        html.Div(
            html.Button(children = 'Add Vessel',
                        className = 'button-primary',
                        id = 'addVessel-button',
                        n_clicks = 0
                ),
            ),
        dcc.Tabs(id='vessel-tabs', style={'padding-top' : 50}, className='control-tabs', value='Vessel 1', children=[
            make_new_vessel_tab('Vessel 1', 1, kerbol_system,
                                'Kerbin', 700000,0,0,0,0,0,4510000,
                                [[1054.39,0,0,4519600.550],
                                 [0,7.03,0,7019695.568],
                                 [-653.34,5.86,0,10867800]]),
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
    html.Div(id='numVessels-div', style={'display': 'none'},
             children=[1]),
    html.Div(id='persistenceVessels-div', style={'display': 'none'},
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
     Output('numVessels-div','children'),
    [Input('numVessels-input', 'value')],
    [State('numVessels-div','children')]
    )
def update_num_vessels(numVessels, prevNumVessels):
    if numVessels == prevNumVessels:
        return dash.no_update
    else:
        return numVessels

@app.callback(
     Output({'type': 'refBody-dropdown', 'index': MATCH}, 'options'),
    [Input('system-div', 'children')]
    )
def update_ref_body_dropdown(system):
    system = jsonpickle.decode(system)
    return name_options(system)

@app.callback(
     Output({'type': 'vessel-tab', 'index': MATCH}, 'label'),
    [Input({'type': 'name-input', 'index': MATCH}, 'value')]
    )
def update_vessel_name(name):
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
            add_maneuver_node(newChildren, ii+prevNumNodes)
    else:
        return dash.no_update
    
    return newChildren

@app.callback(
    [Output('vessel-tabs','children'),
     Output('vessel-tabs','value'),
     Output('numVessels-input','value')],
    [Input('numVessels-div','children'),
     Input('addPersistenceVessel-button','n_clicks'),
     Input('addVessel-button','n_clicks'),
     Input({'type': 'deleteVessel-button', 'index': ALL}, 'n_clicks')],
    [State('vessel-tabs','children'),
     State('vessel-tabs','value'),
     State('system-div','children'),
     State('persistenceVessel-dropdown','value'),
     State('persistenceVessels-div','children')],
    prevent_initial_call=True
    )
def update_vessel_tabs(numVessels,
                       addFileVesselClicks, addVesselClicks, delVesselClicks,
                       prevVesselTabs, prevTabVal, system,
                       addVesselName, persistenceVessels):
    
    system = jsonpickle.decode(system)
    prevNumVessels = len(prevVesselTabs)
    
    tabIdxs = []
    for ii, tab in enumerate(prevVesselTabs):
            tabIdxs.append(tab['props']['children'][0]['props']['children'][0]['props']['id']['index'])
    
    ctx = dash.callback_context
    if ctx.triggered[0]['prop_id'].split('.')[0] == 'addPersistenceVessel-button':
        persistenceVessels = jsonpickle.decode(persistenceVessels)
        vessel = [vs for vs in persistenceVessels if vs.name == addVesselName][0]
        
        vesselTabs = prevVesselTabs
        tabValues = [tab['props']['value'] for tab in vesselTabs]
        if not vessel.name in tabValues:
            vesselTabs.append(
                make_new_vessel_tab(vessel.name, prevNumVessels+1, system,
                                    vessel.orb.prim.name, vessel.orb.a, 
                                    vessel.orb.ecc, vessel.orb.inc, 
                                    vessel.orb.argp, vessel.orb.lan,
                                    vessel.orb.mo, vessel.orb.epoch,
                                    vessel.maneuverNodes)
                )
            numVessels = numVessels+1
            tabVal = vessel.name
        else:
            tabVal = prevTabVal
    
    elif 'deleteVessel-button' in ctx.triggered[0]['prop_id']:
        vesselTabs = prevVesselTabs
        idx = int(str(ctx.triggered[0]['prop_id']).split('.')[0][9])
        for ii, tIdx in enumerate(tabIdxs):
            if tIdx == idx:
                tabIdx = ii
                break
        if prevNumVessels == 1:
            tabVal = None
        elif tabIdx == 0:
            tabVal = vesselTabs[1]['props']['value']
        else:
            tabVal = vesselTabs[tabIdx-1]['props']['value']
        del(vesselTabs[tabIdx])
        numVessels = numVessels-1
    
    elif numVessels < prevNumVessels:
        vesselTabs = prevVesselTabs[0:numVessels]
        try:
            tabVal = vesselTabs[-1]['props']['value']
        except IndexError:
            tabVal = None
    elif (numVessels > prevNumVessels) or ('addVessel-button' in ctx.triggered[0]['prop_id']):
        if numVessels==prevNumVessels:
            numVessels = numVessels+1
        vesselTabs = prevVesselTabs
        newIdx = 1
        for jj in range(numVessels-prevNumVessels):
            while newIdx in tabIdxs:
                newIdx = newIdx+1
            vesselTabs.append(
                make_new_vessel_tab('Vessel '+str(newIdx),                  \
                                    newIdx, system)
                  )
            tabVal = 'Vessel '+str(newIdx)
            tabIdxs.append(newIdx)
        tabOrder = np.argsort(tabIdxs)
        newVesselTabs = []
        for ii in tabOrder:
            newVesselTabs.append(vesselTabs[ii])
        vesselTabs = newVesselTabs
        
    else:
        vesselTabs = prevVesselTabs
        tabVal = prevTabVal
    
    return vesselTabs, tabVal, numVessels

@app.callback(
     Output('orbits-div','children'),
    [Input('plot-button','n_clicks')],
    [State('system-div','children'),
     State('vessel-tabs','children'),
     State('numRevs-input','value')]
    )
def update_orbits(nClicks, system, vesselTabs, numRevs):
    
    # don't update on page load
    if nClicks == 0:
        return dash.no_update
    
    vesselOrbits = []
    vesselTimes = []
    
    for tab in vesselTabs:
        
        # get parameters from tab children
        startBodyName = tab['props']['children'][10]['props']['value']
        startA = tab['props']['children'][12]['props']['value']
        startEcc = tab['props']['children'][14]['props']['value']
        startInc = tab['props']['children'][16]['props']['value']
        startArgP = tab['props']['children'][18]['props']['value']
        startLAN = tab['props']['children'][20]['props']['value']
        startMo = tab['props']['children'][22]['props']['value']
        startEpoch = tab['props']['children'][24]['props']['value']
        
        nodesChildren = tab['props']['children'][28]['props']['children']
        
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
        
        orbits = [sOrb]
        times = [0]
        if len(nodeTimes)>0:
            if nodeTimes[0] < startEpoch:
                times = [nodeTimes[0]-1]
        t = times[0]
        nodeIdx = 0
        stopSearch = False
        while not stopSearch:
            nextOrb, time = orbits[-1].propagate(t+0.1)
            if nextOrb is None:
                for ii in range(numRevs):
                    t = t + orbits[-1].get_period()
                    nextOrb, time = orbits[-1].propagate(t+0.1)
                    if not nextOrb is None:
                        break
            
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
            
            if (nextOrb is None and nodeIdx >= len(nodeTimes)):
                stopSearch = True
        
        vesselOrbits.append(orbits)
        vesselTimes.append(times)
    
    return jsonpickle.encode([vesselOrbits, vesselTimes])

@app.callback(
    [Output('graph-tabs','children'),
     Output('graph-tabs', 'value'),
     Output('orbitStartTimes-div', 'children'),
     Output('orbitEndTimes-div', 'children'),
     Output('plotSystems-div', 'children')],
    [Input('orbits-div','children')],
    [State('startTime-input','value'),
     State('endTime-input','value'),
     State('graph-tabs', 'value')]
    )
def update_graph_tabs(orbitsTimes, startTime, endTime, tabVal):
    
    if orbitsTimes is None:
        return dash.no_update, dash.no_update, dash.no_update,              \
               dash.no_update, dash.no_update
    
    if len(orbitsTimes)<1:
        return dash.no_update, dash.no_update, dash.no_update,              \
               dash.no_update, dash.no_update
    
    vesselOrbitsTimes = jsonpickle.decode(orbitsTimes)
    
    if startTime is None:
        startTime = 0
    
    blankFig = blank_plot(),
    
    tabs = []
    systems = []
    sliderStartTimes = []
    sliderEndTimes = []
    orbitStartTimes = []
    orbitEndTimes = []
    
    for nn in range(len(vesselOrbitsTimes[0])):
        orbits = vesselOrbitsTimes[0][nn]
        times = vesselOrbitsTimes[1][nn]
        sTimes = []
        eTimes = []
        
        eTime = None
        for ii in range(len(orbits)):
            
            orb = orbits[ii]
            sTime = times[ii]
            
            soi = orb.prim.soi
            
            if sTime < startTime:
                if ii < len(times)-1:
                    if not times[ii+1] < startTime:
                        sTime = startTime
            
            if not sTime < startTime:
                if ii == len(orbits)-1:
                    if orb.ecc > 1:
                        if soi is None:
                            maxDist = orb.prim.satellites[-1].orb.a *                   \
                                      (1+orb.prim.satellites[-1].orb.ecc) +             \
                                      orb.prim.satellites[-1].soi;
                        else:
                            maxDist = soi
                        # true anomaly at escape
                        try:
                            thetaEscape = math.acos(1/orb.ecc *                         \
                                                    (orb.a*(1-orb.ecc**2)/maxDist - 1))
                        except ValueError:
                            thetaEscape = math.acos(
                                math.copysign(1, 1/orb.ecc *                            \
                                              (orb.a*(1-orb.ecc**2)/maxDist - 1)))
                        eTime = orb.get_time(thetaEscape)
                    else:
                        if soi is None:
                            eTime = sTime + orb.get_period()
                        else:
                            if orb.a*(1+orb.ecc)>soi:
                                try:
                                    thetaEscape = math.acos(1/orb.ecc *                 \
                                                            (orb.a*(1-orb.ecc**2)/soi - 1))
                                except ValueError:
                                    thetaEscape = math.acos(
                                        math.copysign(1, 1/orb.ecc *                    \
                                                      (orb.a*(1-orb.ecc**2)/soi - 1)))
                                eTime = orb.get_time(thetaEscape)
                            else:
                                eTime = sTime + orb.get_period()
                else:
                    eTime = times[ii+1]
            
            if not eTime is None:
                if not endTime is None:
                    if endTime < eTime:
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
            
            else:
                # save start and end times for each orbit
                sTimes.append(None)
                eTimes.append(None)
                
        orbitStartTimes.append(sTimes)
        orbitEndTimes.append(eTimes)
    
    for jj in range(len(systems)):
        
        if systems[jj] == 'Sun':
            systems[jj] = 'Solar'
        
        tabs.append(dcc.Tab(label=str(systems[jj])+' system',
                            className='control-tab',
                            value=str(systems[jj])+'-tab',
                            children=[
                                dcc.Graph(
                                    id={'type': 'system-graph',
                                        'index': jj},
                                    figure=blankFig),
                                html.Label('Universal Time (s)'),
                                dcc.Input(
                                    id={'type': 'plotTime-input',
                                        'index': jj},
                                    type='number',
                                    value = math.ceil(sliderStartTimes[jj])+1,
                                    min=math.ceil(sliderStartTimes[jj])+1,
                                    max=math.floor(sliderEndTimes[jj])-1,
                                    ),
                                dcc.Slider(
                                    id={'type': 'plotTime-slider',
                                        'index': jj},
                                    min=math.ceil(sliderStartTimes[jj])+1,
                                    max=math.floor(sliderEndTimes[jj])-1,
                                    step=1,
                                    marks = dict(),
                                    value=math.ceil(sliderStartTimes[jj])+1,
                                    included=False,
                                    updatemode='mouseup'
                                    ),
                                html.A(children=html.Button('Download'),
                                       id={'type': 'download-button',
                                           'index': jj},
                                       download=str(systems[jj])+'_system'+'.html',
                                       target="_blank"),
                            ]
                               ))
        
    if not (tabVal[0:-4] in systems):
        try:
            tabVal = systems[0]+'-tab'
        except IndexError:
            tabVal = 'blank-tab'
    
    return tabs, tabVal, orbitStartTimes, orbitEndTimes, systems

@app.callback(
    [Output({'type': 'system-graph', 'index': MATCH}, 'figure'),
     Output({'type': 'download-button', 'index': MATCH}, 'href')],
    [Input({'type': 'plotTime-slider', 'index': MATCH}, 'value'),
     Input('display-checklist','value'),
     Input('dateFormat-div','children')],
    [State('orbits-div','children'),
     State('orbitStartTimes-div','children'),
     State('orbitEndTimes-div', 'children'),
     State('plotSystems-div', 'children'),
     State('vessel-tabs', 'children'),
     State('system-div', 'children'),
     State({'type': 'system-graph', 'index': MATCH}, 'figure')],
    )
def update_graphs(sliderTime, displays, dateFormat,
                  orbitsTimes, orbitStartTimes, orbitEndTimes,
                  plotSystems, vesselTabs,
                  system, prevFig):
    
    figIdx = dash.callback_context.inputs_list[0]['id']['index']
    vesselOrbitsTimes = jsonpickle.decode(orbitsTimes)
    system = jsonpickle.decode(system)
    
    primaryName = plotSystems[figIdx]
    if primaryName == 'Solar':
        primaryName = 'Sun'
    primaryBody = [x for x in system if x.name == primaryName][0]
    
    fig = go.Figure()
    lim = plot_system(fig, primaryBody, sliderTime,                         \
                      dateFormat, displays);
    set_trajectory_plot_layout(fig, lim, uirev = primaryBody.name)
    
    for nn in range(len(vesselOrbitsTimes[0])):
        
        vesselName = vesselTabs[nn]['props']['label']
        
        # prepare color
        color = (                                                           \
            vesselTabs[nn]['props']['children'][5]['props']['value'],       \
            vesselTabs[nn]['props']['children'][6]['props']['value'],       \
            vesselTabs[nn]['props']['children'][7]['props']['value']        \
                )
        
        # prepare maneuver nodes
        nodesChildren = vesselTabs[nn]['props']['children'][28]['props']['children']
        nodeBurns = []
        nodeTimes = []
        for kk in range(int(len(nodesChildren)/5)):
            nodeBurns.append([nodesChildren[5*kk+1]["props"]["value"],
                              nodesChildren[5*kk+2]["props"]["value"],
                              nodesChildren[5*kk+3]["props"]["value"],
                              ])
            nodeTimes.append(nodesChildren[5*kk+4]['props']['value'])
        
        orbits = vesselOrbitsTimes[0][nn]
        sTimes = orbitStartTimes[nn]
        eTimes = orbitEndTimes[nn]
        
        for ii in range(len(orbits)):
            orb = orbits[ii]
            sTime = sTimes[ii]
            eTime = eTimes[ii]
            
            if not ((sTime is None) or (eTime is None)) and                 \
               orb.prim.name==primaryBody.name:
                
                # draw orbits
                if 'orbits' in displays:
                    add_orbit(fig, orb, sTime, eTime, 201,
                          dateFormat, 'apses' in displays, 'nodes' in displays,
                          fullPeriod=False, color=color, name=vesselName,
                          style='solid', fade=True)
                
                # add burn arrows
                if (eTime in nodeTimes) and ('arrows' in displays):
                    burnIdx = nodeTimes.index(eTime)
                    burnDV = nodeBurns[burnIdx]
                    add_burn_arrow(fig, burnDV, eTime, orb, dateFormat,
                                   1/2, 'Burn'+str(burnIdx+1), color, False)
                
                # add vessel marker
                if (sTime<sliderTime) and ((sliderTime<eTime) or ((ii==len(orbits)-1) and (orb.ecc<1))):
                    vessel = Body('Vessel'+str(nn+1),0,0,0,orb,color=color)
                    add_body(fig, vessel, sliderTime, False, size = 4, symbol = 'square')
    
            elif (ii==len(orbits)-1) and (orb.ecc<1) and                            \
                 orb.prim.name==primaryBody.name:
                
                # draw orbits
                if 'orbits' in displays:
                    add_orbit(fig, orb, sliderTime, sliderTime+orb.get_period(), 201,
                          dateFormat, 'apses' in displays, 'nodes' in displays,
                          fullPeriod=False, color=color, name=vesselName,
                          style='solid', fade=True)
                
                # add burn arrows
                if (eTime in nodeTimes) and ('arrows' in displays):
                    burnIdx = nodeTimes.index(eTime)
                    burnDV = nodeBurns[burnIdx]
                    add_burn_arrow(fig, burnDV, eTime, orb, dateFormat,
                                   1/2, 'Burn'+str(burnIdx+1), color, False)
                
                # add vessel marker
                vessel = Body('Vessel'+str(nn+1),0,0,0,orb,color=color)
                add_body(fig, vessel, sliderTime, False, size = 4, symbol = 'square')
    
    # create downloadable HTML file of plot
    filename = plotSystems[figIdx]+'_system.html'
    path = os.path.join(DOWNLOAD_DIRECTORY, filename)
    location = "/download/{}".format(urlquote(filename))
    fig.write_html(path)
    
    return fig, location

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
    [Output('persistenceVessels-div', 'children'),
     Output('persistenceVessel-dropdown', 'options'),
     Output('persistenceVessel-dropdown', 'value')],
    [Input('persistenceFile-upload', 'contents')],
    [State('system-div', 'children')],
     prevent_initial_call=True
      )
def create_vessels_from_persistence_file(persistenceFile, system):
    
    if persistenceFile is None:
        return dash.no_update, dash.no_update, dash.no_update
    
    system = jsonpickle.decode(system)
    persistenceFile = persistenceFile.split(',')[1]
    persistenceFile = b64decode(persistenceFile).decode('utf-8')
    sfsData = parse_savefile(persistenceFile, False)
    sfsVessels = sfsData['GAME']['FLIGHTSTATE']['VESSEL']
    vessels = []
    for sfsVessel in sfsVessels:
        
        name = sfsVessel['name']
        
        a = float(sfsVessel['ORBIT']['SMA'])
        ecc = float(sfsVessel['ORBIT']['ECC'])
        inc = float(sfsVessel['ORBIT']['INC'])
        argp = float(sfsVessel['ORBIT']['LPE'])
        lan = float(sfsVessel['ORBIT']['LAN'])
        mo = float(sfsVessel['ORBIT']['MNA'])
        epoch = float(sfsVessel['ORBIT']['EPH'])
        if 'IDENT' in list(sfsVessel['ORBIT'].keys()):
            primName = sfsVessel['ORBIT']['IDENT']
            primName = primName.replace('Squad/','')
            prim = [bd for bd in system if bd.name == primName][0]
        else:
            primRef = float(sfsVessel['ORBIT']['REF'])
            prim = [bd for bd in system if bd.ref == primRef][0]
        
        if not a == 0:
            orb = Orbit(a, ecc, inc, argp, lan, mo, epoch, prim)
        
            try:
                sfsManeuverNodes = sfsVessel['FLIGHTPLAN']['MANEUVER']
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
            
            vessels.append(Vessel(name, orb, maneuverNodes))
    
    vesselOptions = name_options(vessels)
    
    return jsonpickle.encode(vessels), vesselOptions, vessels[0].name

#%% run app

if __name__ == '__main__':
    app.run_server(debug=False)