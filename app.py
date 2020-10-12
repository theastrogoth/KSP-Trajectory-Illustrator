import os
from flask import Flask, send_from_directory
from urllib.parse import quote as urlquote

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State, ALL, MATCH
import plotly.graph_objects as go
from plotutils import *

import jsonpickle
import math
import numpy as np
from numpy.linalg import norm
from orbit import Orbit
from body import Body

DOWNLOAD_DIRECTORY = "/tmp/app_generated_files"

if not os.path.exists(DOWNLOAD_DIRECTORY):
    os.makedirs(DOWNLOAD_DIRECTORY)

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

server = Flask(__name__)
app = dash.Dash(__name__, external_stylesheets=external_stylesheets,
                server=server)

app.title='KSP Trajectory Illustrator'

#%% read solar system data
infile = open('kerbol_system.json','r')
kerbol_system = jsonpickle.decode(infile.read())
infile.close
infile = open('sol_system.json','r')
sol_system = jsonpickle.decode(infile.read())
infile.close

#%%
def startBody_options(system):
    start_bodies = []
    for bd in system:
        start_bodies.append(bd.name) 
    return [{'label': i, 'value': i} for i in start_bodies]

#%% download functions

@app.server.route('/download/<path:path>')
def serve_static(path):
    return send_from_directory(DOWNLOAD_DIRECTORY, path, as_attachment=True)

#%% app layout

app.layout = html.Div(className='row', children=[
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
                {'label': 'Kerbol', 'value': 'Kerbol'},
                {'label': 'Sol', 'value': 'Sol'}],
            value='Kerbol',
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
                  value = 4515000),
        html.Label('End time (s)'),
        dcc.Input(id = 'endTime-input',  
                  type='number'),
        html.Label('Max number of patched conics'),
        dcc.Input(id = 'numPatches-input',  
                  type='number',
                  value = 10,
                  min = 0,
                  step = 1),
        html.Label('Number of vessels'),
        dcc.Input(id = 'numVessels-input',  
                  type='number',
                  value = 2,
                  min = 1,
                  step = 1),
        ]),
    
    
    html.Div(className='four columns', children=[
        
        dcc.Tabs(id='vessel-tabs', value='vessel1', children=[
            dcc.Tab(label='Vessel 1', value='vessel1', children=[
                html.H3('Plot Style'),                                  #0
                html.Label('Color (RGB)'),                              #1
                dcc.Input(type='number',                                #2
                          min=0,
                          max=255,
                          value=255),
                dcc.Input(type='number',                                #3
                          min=0,
                          max=255,
                          value=255),
                dcc.Input(type='number',                                #4
                          min=0,
                          max=255,
                          value=255),
                html.H3('Starting Orbit'),                              #5
                html.Label('Starting Body'),                            #6
                dcc.Dropdown(                                           #7
                    value = 'Kerbin',
                    options = startBody_options(kerbol_system)
                    ),
                html.Label('Semi-major axis (m)'),                      #8
                dcc.Input(type='number',                                #9
                          value = 700000),
                html.Label('Eccentricity'),                             #10
                dcc.Input(type='number',                                #11
                          value = 0),
                html.Label('Inclination (°)'),                          #12
                dcc.Input(type='number',                                #13
                          value = 0),
                html.Label('Argument of the Periapsis (°)'),            #14
                dcc.Input(type='number',                                #15
                          value = 0),
                html.Label('Longitude of the Ascending Node (°)'),      #16
                dcc.Input(type='number',                                #17
                          value = 0),
                html.Label('Mean anomaly at epoch (radians)'),          #18
                dcc.Input(type='number',                                #19
                          value = 0),
                html.Label('Epoch (s)'),                                #20
                dcc.Input(type='number',                                #21
                          value = 4510000),
        
                html.H3('Maneuver Nodes'),                              #22
                html.Label('Number of maneuver nodes'),                 #23
                dcc.Input(id={'type': 'numNodes-input',                 #24
                              'index': 1},
                          type = 'number',
                          value = 3,
                          min = 0,
                          step = 1),
                html.Div(children=[                                     #25
                    html.Label('Maneuver node 1'),                  #0
                    dcc.Input(type='number',                        #1
                              placeholder='Prograde (m/s)',
                              value=1054.39),
                    dcc.Input(type='number',                        #2
                              placeholder='Normal (m/s)',
                              value=0),
                    dcc.Input(type='number',                        #3
                              placeholder='Radial (m/s)',
                              value=0),
                    dcc.Input(type='number',                        #4
                              placeholder='UT (s)',
                              value=4519600.550),
                    html.Label('Maneuver node 2'),
                    dcc.Input(type='number',
                              placeholder='Prograde (m/s)',
                              value=0),
                    dcc.Input(type='number',
                              placeholder='Normal (m/s)',
                              value=7.03),
                    dcc.Input(type='number',
                              placeholder='Radial (m/s)',
                              value=0),
                    dcc.Input(type='number',
                              placeholder='UT (s)',
                              value=7019695.568),
                    html.Label('Maneuver node 3'),
                    dcc.Input(type='number',
                              placeholder='Prograde (m/s)',
                              value=-653.34),
                    dcc.Input(type='number',
                              placeholder='Normal (m/s)',
                              value=5.86),
                    dcc.Input(type='number',
                              placeholder='Radial (m/s)',
                              value=0),
                    dcc.Input(type='number',
                              placeholder='UT (s)',
                              value=10867800),
                    ]),
                ]),
            dcc.Tab(label='Vessel 2', value='vessel2', children=[
                html.H3('Plot Style'),                                  #0
                html.Label('Color (RGB)'),                              #1
                dcc.Input(type='number',                                #2
                          min=0,
                          max=255,
                          value=0),
                dcc.Input(type='number',                                #3
                          min=0,
                          max=255,
                          value=255),
                dcc.Input(type='number',                                #4
                          min=0,
                          max=255,
                          value=0),
                html.H3('Starting Orbit'),                              #5
                html.Label('Starting Body'),                            #6
                dcc.Dropdown(                                           #7
                    value = 'Duna',
                    options = startBody_options(kerbol_system)
                    ),
                html.Label('Semi-major axis (m)'),                      #8
                dcc.Input(type='number',                                #9
                          value = 420000),
                html.Label('Eccentricity'),                             #10
                dcc.Input(type='number',                                #11
                          value = 0),
                html.Label('Inclination (°)'),                          #12
                dcc.Input(type='number',                                #13
                          value = 0),
                html.Label('Argument of the Periapsis (°)'),            #14
                dcc.Input(type='number',                                #15
                          value = 0),
                html.Label('Longitude of the Ascending Node (°)'),      #16
                dcc.Input(type='number',                                #17
                          value = 0),
                html.Label('Mean anomaly at epoch (radians)'),          #18
                dcc.Input(type='number',                                #19
                          value = 0),
                html.Label('Epoch (s)'),                                #20
                dcc.Input(type='number',                                #21
                          value = 0),
        
                html.H3('Maneuver Nodes'),                              #22
                html.Label('Number of maneuver nodes'),                 #23
                dcc.Input(id={'type': 'numNodes-input',                 #24
                              'index': 2},
                          type = 'number',
                          value = 0,
                          min = 0,
                          step = 1),
                html.Div(children=[]                                    #25
                     ),
                ]),
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
        dcc.Tabs(id='conic-tabs', value='blank', children=[
            dcc.Tab(label='Plots will be generated here', value='blank', children=[
                dcc.Graph(
                    id='blank',
                    figure = go.Figure(layout = dict(
                                        xaxis = dict(visible=False),
                                        yaxis = dict(visible=False))),
                    )
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
                 jsonpickle.encode(sol_system)]),
    html.Div(id='system-div', style={'display': 'none',}, 
             children=jsonpickle.encode(kerbol_system)),
    html.Div(id='numManeuverNodes-div', style={'display': 'none'},
             children=[3,0]),
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
     Output('system-div', 'children'),
    [Input('system-radio','value'),
     Input('systemResize-input','value'),
     Input('systemRescale-input','value')],
    [State('allSystems-div', 'children')]
    )
def set_system(system_name, resizeFactor, rescaleFactor, all_systems):
    if system_name == 'Kerbol':
        system = jsonpickle.decode(all_systems[0])
    elif system_name == 'Sol':
        system = jsonpickle.decode(all_systems[1])
    else:
        return dash.no_update, dash.no_update
    
    for body in system:
        body.resize(resizeFactor)
        body.rescale(rescaleFactor)
    
    return jsonpickle.encode(system)

@app.callback(
     Output('numManeuverNodes-div','children'),
    [Input({'type': 'numNodes-input', 'index': ALL}, 'value')],
    [State('numManeuverNodes-div','children')],
    prevent_initial_call=True
    )
def update_num_maneuver_nodes(numsNodes, prevState):
    # print('update_num_maneuver_nodes called')
    # print(numsNodes)
    if prevState == numsNodes:
        # print('no update')
        return dash.no_update
    else:
        return numsNodes

@app.callback(
    [Output('vessel-tabs','children'),
     Output('vessel-tabs','value')],
    [Input('numVessels-input','value'),
     Input('numManeuverNodes-div','children')],
    [State('vessel-tabs','children'),
     State('vessel-tabs','value'),
     State('system-div','children')],
    prevent_initial_call=True
    )
def update_vessel_tabs(numVessels, numsNodes, prevVesselTabs, prevTabVal, system):
    system = jsonpickle.decode(system)
    prevNumVessels = len(prevVesselTabs)
    if numVessels < prevNumVessels:
        vesselTabs = prevVesselTabs[0:numVessels]
    elif numVessels > prevNumVessels:
        vesselTabs = prevVesselTabs
        for jj in range(numVessels-prevNumVessels):
          vesselTabs.append(                                                \
            dcc.Tab(label='Vessel ' + str(jj+prevNumVessels+1),             \
                    value='vessel' + str(jj+prevNumVessels+1), 
                    children=[
                html.H3('Plot Style'),                                  #0
                # doesn't do anything yet
                html.Label('Color (RGB)'),                              #1
                dcc.Input(type='number',                                #2
                          min=0,
                          max=255,
                          value=255),
                dcc.Input(type='number',                                #3
                          min=0,
                          max=255,
                          value=255),
                dcc.Input(type='number',                                #4
                          min=0,
                          max=255,
                          value=255),
                html.H3('Starting Orbit'),                              #5
                html.Label('Starting Body'),                            #6
                dcc.Dropdown(                                           #7
                    options = startBody_options(system)
                    ),
                html.Label('Semi-major axis (m)'),                      #8
                dcc.Input(type='number',                                #9
                          value = 0),
                html.Label('Eccentricity'),                             #10
                dcc.Input(type='number',                                #11
                          value = 0),
                html.Label('Inclination (°)'),                          #12
                dcc.Input(type='number',                                #13
                          value = 0),
                html.Label('Argument of the Periapsis (°)'),            #14
                dcc.Input(type='number',                                #15
                          value = 0),
                html.Label('Longitude of the Ascending Node (°)'),      #16
                dcc.Input(type='number',                                #17
                          value = 0),
                html.Label('Mean anomaly at epoch (radians)'),          #18
                dcc.Input(type='number',                                #19
                          value = 0),
                html.Label('Epoch (s)'),                                #20
                dcc.Input(type='number',                                #21
                          value = 0),
        
                html.H3('Maneuver Nodes'),                              #22
                html.Label('Number of maneuver nodes'),                 #23
                dcc.Input(id={'type': 'numNodes-input',                 #24
                              'index': jj+prevNumVessels+1},
                          type = 'number',
                          value = 0,
                          min = 0,
                          step = 1),
                html.Div(children=[]                                    #25
                    ),
                ])
              )
    else:
        vesselTabs = prevVesselTabs
    
    for ii, numNodes in enumerate(numsNodes[0:numVessels]):
        try:
            prevNumNodes = int(len(vesselTabs[ii]['props']['children'][25]['props']['children'])/5)
        except:
            prevNumNodes = int(len(vesselTabs[ii].children[25].children)/5)
        if numNodes < prevNumNodes:
            vesselTabs[ii]['props']['children'][25]['props']['children'] = \
                vesselTabs[ii]['props']['children'][25]['props']['children'][0:5*(numNodes)];
        elif numNodes > prevNumNodes:
            for jj in range(numNodes-prevNumNodes):
                vesselTabs[ii]['props']['children'][25]['props']['children'].append( \
                    html.Label('Maneuver node '+str(jj+prevNumNodes+1)))
                vesselTabs[ii]['props']['children'][25]['props']['children'].append( \
                    dcc.Input(type='number',placeholder='Prograde (m/s)'));
                vesselTabs[ii]['props']['children'][25]['props']['children'].append( \
                    dcc.Input(type='number',placeholder='Normal (m/s)'));
                vesselTabs[ii]['props']['children'][25]['props']['children'].append( \
                    dcc.Input(type='number',placeholder='Radial (m/s)'));
                vesselTabs[ii]['props']['children'][25]['props']['children'].append( \
                    dcc.Input(type='number',placeholder='UT (s)'));
        
    
    if len(vesselTabs) < int(prevTabVal[-1]):
        tabVal = 'vessel'+str(len(vesselTabs))
    else:
        tabVal = prevTabVal
    
    return vesselTabs, tabVal

@app.callback(
     Output('orbits-div','children'),
    [Input('plot-button','n_clicks')],
    [State('system-div','children'),
     State('vessel-tabs','children'),
     State('startTime-input','value'),
     State('endTime-input','value'),
     State('numPatches-input','value')]
    )
def update_orbits(nClicks, system, vesselTabs,
                  startTime, endTime, numPatches):
    
    # don't update on page load
    if nClicks == 0:
        return dash.no_update
    
    vesselOrbits = []
    vesselTimes = []
    
    for tab in vesselTabs:
        
        # get parameters from tab children
        startBodyName = tab['props']['children'][7]['props']['value']
        startA = tab['props']['children'][9]['props']['value']
        startEcc = tab['props']['children'][11]['props']['value']
        startInc = tab['props']['children'][13]['props']['value']
        startArgP = tab['props']['children'][15]['props']['value']
        startLAN = tab['props']['children'][17]['props']['value']
        startMo = tab['props']['children'][19]['props']['value']
        startEpoch = tab['props']['children'][21]['props']['value']
        
        nodesChildren = tab['props']['children'][25]['props']['children']
        
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
        times = [startTime]
        t = startTime
        nodeIdx = 0
        for num in range(numPatches+len(nodeTimes)):
            if not (endTime is None):
                if t > endTime:
                    break
            nextOrb, time = orbits[-1].propagate(t+0.1)
            if nextOrb is None:
                t = t + orbits[-1].get_period()
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
        
        vesselOrbits.append(orbits)
        vesselTimes.append(times)
    
    return jsonpickle.encode([vesselOrbits, vesselTimes])

@app.callback(
    [Output('conic-tabs','children'),
     Output('conic-tabs', 'value')],
    [Input('orbits-div','children'),
     Input('dateFormat-div','children'),
     Input('display-checklist', 'value'),
     Input('endTime-input','value')],
    [State('conic-tabs', 'value'),
     State('vessel-tabs', 'children')]
    )
def update_graphs(orbitsTimes, dateFormat, displays, endTime, tabVal, 
                  vesselTabs):
    
    if orbitsTimes is None:
        return dash.no_update
    
    vesselOrbitsTimes = jsonpickle.decode(orbitsTimes)
    
    tabs = []
    figs = []
    systems = []
    
    for nn in range(len(vesselOrbitsTimes[0])):
        orbits = vesselOrbitsTimes[0][nn]
        times = vesselOrbitsTimes[1][nn]
    
        color = (                                                           \
            vesselTabs[nn]['props']['children'][2]['props']['value'],       \
            vesselTabs[nn]['props']['children'][3]['props']['value'],       \
            vesselTabs[nn]['props']['children'][4]['props']['value']        \
                )
        
        # prepare maneuver nodes
        nodesChildren = vesselTabs[nn]['props']['children'][25]['props']['children']
        nodeBurns = []
        nodeTimes = []
        for kk in range(int(len(nodesChildren)/5)):
            nodeBurns.append([nodesChildren[5*kk+1]["props"]["value"],
                              nodesChildren[5*kk+2]["props"]["value"],
                              nodesChildren[5*kk+3]["props"]["value"],
                              ])
            nodeTimes.append(nodesChildren[5*kk+4]['props']['value'])
        
        for ii in range(len(orbits)):
            
            orb = orbits[ii]
            sTime = times[ii]
            
            soi = orb.prim.soi
            
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
            
            if not endTime is None:
                if endTime < eTime:
                    eTime = endTime
            
            if orb.prim.name in systems:
                figIdx = systems.index(orb.prim.name)
            else:
                figs.append(go.Figure())
                systems.append(orb.prim.name)
                figIdx = -1
                lim = plot_system(figs[figIdx], orb.prim, times[ii],            \
                      dateFormat, displays);
                set_trajectory_plot_layout(figs[figIdx], lim, 1.5*abs(orb.a)/lim, orb.prim.name)
            
            if 'orbits' in displays:
                add_orbit(figs[figIdx], orb, sTime, eTime, 201,
                      dateFormat, 'apses' in displays, 'nodes' in displays,
                      fullPeriod=False, color=color, name='Conic '+str(ii+1),
                      style='solid', fade=True)
            
            # add burn arrows
            if (eTime in nodeTimes) and ('arrows' in displays):
                burnIdx = nodeTimes.index(eTime)
                burnDV = nodeBurns[burnIdx]
                print(burnDV)
                add_burn_arrow(figs[figIdx], burnDV, eTime, orb, dateFormat,
                               1/2, 'Burn'+str(burnIdx+1), (255,0,0), False)
            
            if not endTime is None:
                if eTime >= endTime:
                    break
        
    for jj in range(len(figs)):
        
        # create downloadable HTML file of plot
        filename = 'System'+str(jj+1)+'.html'
        path = os.path.join(DOWNLOAD_DIRECTORY, filename)
        location = "/download/{}".format(urlquote(filename))
        figs[jj].write_html(path)
        
        tabs.append(dcc.Tab(label=str(systems[jj])+' system',
                           value=str(systems[jj])+'-tab',
                           children=[dcc.Graph(
                                           id=str(systems[jj])+'-graph',
                                           figure=figs[jj]),
                            html.A(children=html.Button('Download'),
                                   id='Conic'+str(jj+1)+'-download',
                                   download='Conic'+str(jj+1)+'.html',
                                   href=location,
                                   target="_blank"),
                            ]
                               ))
        
    if not (tabVal[0:-4] in systems):
        tabVal = systems[0]+'-tab'
    
    return tabs, tabVal


#%% run app

if __name__ == '__main__':
    app.run_server(debug=False)