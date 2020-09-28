import os
from flask import Flask, send_from_directory
from urllib.parse import quote as urlquote

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
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
                  value = 5283000),
        html.Label('End time (s)'),
        dcc.Input(id = 'endTime-input',  
                  type='number'),
        html.Label('Max number of patched conics'),
        dcc.Input(id = 'numPatches-input',  
                  type='number',
                  value = 10,
                  min = 0,
                  step = 1),
        
        html.H3('Starting Orbit'),
        html.Label('Starting Body'),
            dcc.Dropdown(
                id = 'startingBody-dropdown',
                value = 'Kerbin'
                ),
        html.Label('Semi-major axis (m)'),
        dcc.Input(id = 'starta-input',  
                  type='number',
                  value = 0),
        html.Label('Eccentricity'),
        dcc.Input(id = 'startecc-input',  
                  type='number',
                  value = 0),
        html.Label('Inclination (°)'),
        dcc.Input(id = 'startinc-input',  
                  type='number',
                  value = 0),
        html.Label('Argument of the Periapsis (°)'),
        dcc.Input(id = 'startargp-input',  
                  type='number',
                  value = 0),
        html.Label('Longitude of the Ascending Node (°)'),
        dcc.Input(id = 'startlan-input',  
                  type='number',
                  value = 0),
        html.Label('Mean anomaly at epoch (radians)'),
        dcc.Input(id = 'startmo-input',  
                  type='number',
                  value = 0),
        html.Label('Epoch (s)'),
        dcc.Input(id = 'startepoch-input',  
                  type='number',
                  value = 0),
        ]),
    html.Div(className='four columns', children=[
        html.H3('Maneuver Nodes'),
        html.Label('Number of maneuver nodes'),
        dcc.Input(id = 'numManeuverNodes-input',
                  type = 'number',
                  value = 1,
                  min = 0,
                  step = 1),
        html.Div(id='maneuverNodes-div', children=[
            html.Label('Maneuver node 1'),
            dcc.Input(type='number',
                      placeholder='Prograde (m/s)',
                      value=1039.87),
            dcc.Input(type='number',
                      placeholder='Normal (m/s)',
                      value=161.37),
            dcc.Input(type='number',
                      placeholder='Radial (m/s)',
                      value=0),
            dcc.Input(type='number',
                      placeholder='UT (s)',
                      value=5284684.055),
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
    # html.Div(id='maneuverNodes-div', style = {'display': 'none'}),
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
    [Output('system-div', 'children'),
     Output('startingBody-dropdown', 'value')],
    [Input('system-radio','value'),
     Input('systemResize-input','value'),
     Input('systemRescale-input','value')],
    [State('allSystems-div', 'children')]
    )
def set_system(system_name, resizeFactor, rescaleFactor, all_systems):
    if system_name == 'Kerbol':
        system = jsonpickle.decode(all_systems[0])
        sBody = 'Kerbin'
    elif system_name == 'Sol':
        system = jsonpickle.decode(all_systems[1])
        sBody = 'Earth'
    else:
        return dash.no_update, dash.no_update
    
    for body in system:
        body.resize(resizeFactor)
        body.rescale(rescaleFactor)
    
    return jsonpickle.encode(system), sBody

@app.callback(
    Output('startingBody-dropdown', 'options'),
    [Input('system-div', 'children')]
    )
def set_startBody_options(system_data):
    system_data_d = jsonpickle.decode(system_data)
    start_bodies = []
    for bd in system_data_d:
        start_bodies.append(bd.name) 
    return [{'label': i, 'value': i} for i in start_bodies]

@app.callback(
     Output('starta-input', 'value'),
    [Input('startingBody-dropdown', 'value')],
    [State('system-div', 'children')],
    )
def update_start_a(start_body_name, system_data):
    system_data_d = jsonpickle.decode(system_data)
    start_body = [x for x in system_data_d if x.name == start_body_name][0]
    return start_body.eqr + 100000

@app.callback(
     Output('maneuverNodes-div','children'),
    [Input('numManeuverNodes-input','value')],
    prevent_initial_call=True
    )
def update_num_maneuver_nodes(num):
    children = []
    for ii in range(1,num+1):
        children.append(html.Label('Maneuver node '+str(ii)))
        children.append(dcc.Input(type='number',placeholder='Prograde (m/s)'))
        children.append(dcc.Input(type='number',placeholder='Normal (m/s)'))
        children.append(dcc.Input(type='number',placeholder='Radial (m/s)'))
        children.append(dcc.Input(type='number',placeholder='UT (s)'))
    
    return children

@app.callback(
     Output('orbits-div','children'),
    [Input('plot-button','n_clicks')],
    [State('system-div','children'),
     State('startingBody-dropdown','value'),
     State('starta-input','value'),
     State('startecc-input','value'),
     State('startinc-input','value'),
     State('startargp-input','value'),
     State('startlan-input','value'),
     State('startmo-input','value'),
     State('startepoch-input','value'),
     State('startTime-input','value'),
     State('endTime-input','value'),
     State('maneuverNodes-div','children'),
     State('numPatches-input','value')]
    )
def update_orbits(nClicks, system, startBodyName,
                  startA, startEcc, startInc, startArgP,
                  startLAN, startMo, startEpoch,
                  startTime, endTime, nodesChildren, numPatches):
    
    # don't update on page load
    if nClicks == 0:
        return dash.no_update
    
    # prepare system information, start body
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
        nodeTimes.append(nodesChildren[5*ii+4]["props"]["value"])
    
    orbits = [sOrb]
    times = [startTime]
    t = startTime
    nodeIdx = 0
    for num in range(numPatches+len(nodeTimes)):
        if not (endTime is None):
            if t > endTime:
                break
        nextOrb, time = orbits[-1].propagate(t+1)
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
    
    return jsonpickle.encode([orbits, times])

@app.callback(
    [Output('conic-tabs','children'),
     Output('conic-tabs', 'value')],
    [Input('orbits-div','children'),
     Input('dateFormat-div','children'),
     Input('display-checklist', 'value'),
     Input('endTime-input','value')],
    [State('conic-tabs', 'value')]
    )
def update_graphs(orbitsTimes, dateFormat, displays, endTime, tabVal):
    
    if orbitsTimes is None:
        return dash.no_update
    
    orbitsTimes = jsonpickle.decode(orbitsTimes)
    orbits = orbitsTimes[0]
    times = orbitsTimes[1]
    
    tabs = []
    figs = []
    systems = []
    
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
        
        add_orbit(figs[figIdx], orb, sTime, eTime, 201,
              dateFormat, 'apses' in displays, 'nodes' in displays,
              fullPeriod=False, color=(255,255,255), name='Conic '+str(ii+1),
              style='solid', fade=True,)
        
        if not endTime is None:
            if eTime == endTime:
                break
    
    for jj in range(len(figs)):
        tabs.append(dcc.Tab(label=str(systems[jj])+' system',
                           value=str(systems[jj])+'-tab',
                           children=dcc.Graph(
                                           id=str(systems[jj])+'-graph',
                                           figure=figs[jj])))
    
    if not (tabVal[0:-4] in systems):
        tabVal = systems[0]+'-tab'
    
    return tabs, tabVal


#%% run app

if __name__ == '__main__':
    app.run_server(debug=False)