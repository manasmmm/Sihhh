# OceanEmbed: Demo Video Script (SIH 2026, SIH26066, Team Crisis Workers)

Covers the whole website except the Fisheries Advisory tab. The confidence layer is left out.
The narration follows one continuous path: the problem, the model, the surface, going deeper,
moving through time, one location in detail, the ocean's structure, the big picture, trust, and data access.

## Before you record

1. **Use model-output mode.** Use the deployed site, or locally run `$env:DATA_SOURCE="files"; python backend/main.py`. The badge in the top right must be green ("MODEL OUTPUT").
2. **Wake the site.** If you use Render, open it a minute early so the free server is awake.
3. **Starting state:** Explorer tab, depth 0 m, Layer "Temperature", Map "Satellite (Sentinel-2)", colour bar on "Auto", no cards open.
4. **Stay on the Explorer tab.** Don't open the Fisheries Advisory tab, and skip "Confidence (data density)" in the Layer menu.
5. **Scene 11:** only hover over "Upload model output"; don't upload a file.
6. **Pacing:** each scene's screen action is written to fit its narration. If the voice runs ahead, pause the recording between scenes; cuts fall naturally at scene boundaries.

---

### Scene 1: The problem

**[SCREEN ACTION]:** Site open on the Explorer tab. Slowly zoom out until the whole North Indian Ocean, from the Arabian Sea to the Bay of Bengal, fills the screen.

**[NARRATION]:** Hello, we are Team Crisis Workers, and this is OceanEmbed, our solution for Smart India Hackathon problem statement S I H two six zero six six. Satellites give us a picture of the ocean surface every day. But just a few hundred meters below, the temperature decides where fish gather, how strong a cyclone can grow, and how the monsoon behaves. Measuring it directly needs ships and floats, and they are few and far apart. OceanEmbed fills that gap.

### Scene 2: How the model works

**[SCREEN ACTION]:** Hold the full-basin view. Move the cursor to "Graph Neural Network (GNN-OAM)" under the panel title and rest it there.

**[NARRATION]:** At its heart is a graph neural network, supported by an X G Boost stage. The model looks back over thirty days of seven satellite measurements: sea surface temperature, salinity, sea surface height, currents and winds. It treats the ocean as a connected network, where each point learns from its neighbours in space and in depth. The result is temperature at fifteen depths, down to one thousand meters, on a zero point two five degree grid.

### Scene 3: Reading the dashboard

**[SCREEN ACTION]:** Move the cursor along the header: first the date stamp in the middle ("Product date … Valid upto … Generated"), then the green "MODEL OUTPUT" badge on the right.

**[NARRATION]:** Let us open the dashboard. The header shows the date of the product and how long it stays valid. The green badge confirms that everything on screen comes from our trained model.

### Scene 4: The surface

**[SCREEN ACTION]:** Point at a warm area, then a cooler area of the map. Then point at the colour bar at the bottom right. Click its "Auto" button to switch to the fixed "0-32°C" scale, pause, and click again to return to "Auto".

**[NARRATION]:** We begin at the surface. Bright colours show warm water, and darker colours show cooler water. The colour scale adapts to each depth, so small differences stand out. For a fair comparison, it can also be fixed from zero to thirty two degrees Celsius.

### Scene 5: Going deeper

**[SCREEN ACTION]:** On the depth rail on the right, click 50 m, then 100 m, then 200 m, then 500 m, pausing on each. Finish at 100 m.

**[NARRATION]:** Now let us go below the surface. The depth rail takes us through all fifteen levels. At fifty meters, the pattern still resembles the surface. By one hundred meters, it changes completely, as we enter the thermocline, where temperature falls quickly with depth. This is the ocean that satellites cannot see.

### Scene 6: Moving through time

**[SCREEN ACTION]:** At 100 m, drag the time slider across a few days. Press Play, change speed from 4 to 10, let it run for about five seconds, then press Pause. Click the "start of period" button.

**[NARRATION]:** The ocean is never still. You can step through the days one by one, or press play and watch it evolve at three speeds, as eddies drift and warm pools grow and shrink.

### Scene 7: One location in detail

**[SCREEN ACTION]:** Click an ocean point in the central Arabian Sea. Point at the large temperature value, then the "Temperature Over Time" chart and its Min / Median / Max row, then the vertical profile chart.

**[NARRATION]:** To understand a single place, simply click on it. The inspection card shows the temperature at the chosen depth, and a time series across every day, with its minimum, median and maximum. Below it is the full vertical profile, from the surface to one thousand meters.

### Scene 8: What the profile tells us

**[SCREEN ACTION]:** Point at the yellow MLD line on the profile, then the pink D20 line. Click a second point in the Bay of Bengal so two cards sit side by side. Point at the download icon on a card.

**[NARRATION]:** Two lines on the profile carry special meaning. The yellow line is the mixed layer, the upper water stirred by the wind. The pink line is the warm layer depth, where the water cools to twenty degrees Celsius, a widely used marker of the thermocline. You can compare up to four locations side by side, and export each one.

### Scene 9: From temperature to ocean structure

**[SCREEN ACTION]:** Close the cards with the bin icon. In the Layer menu choose "Warm-layer depth (D20)" and pause. Then "Mixed-layer depth (MLD)". Then "Front strength at 50 m", pointing at the white threshold mark on the legend. Then "Subsurface-only fronts".

**[NARRATION]:** OceanEmbed also goes beyond temperature. The layer menu turns each day into maps of ocean structure. They show where the thermocline sits, how deep the upper ocean is mixed, and where sharp fronts separate different water masses. Such fronts are often rich in nutrients. We show them at the surface, at fifty meters and at one hundred meters. One layer even reveals fronts that exist below the surface but are invisible from space.

### Scene 10: The bigger picture

**[SCREEN ACTION]:** Set Layer back to "Temperature". Click "Basin Mean" and let the chart appear; close it. Click "Argo Truth" and click one float marker to open its popup; then turn Argo Truth off. In the Map menu choose "NASA Blue Marble + sea floor", drag the Opacity slider down and back up, then return the map to "Satellite (Sentinel-2)".

**[NARRATION]:** Stepping back, the basin mean chart tracks the average temperature of the whole region over time. The Argo layer marks Argo floats, robotic instruments that measure real temperature profiles as they drift. And you can choose from five background maps, and adjust how strongly the data is shown.

### Scene 11: Can we trust it?

**[SCREEN ACTION]:** Click "Validation". Point at the chart, then slowly move down the table: first the rows from 0 to 30 m, then the deeper rows.

**[NARRATION]:** A reconstruction is only useful if it can be trusted. The validation panel compares our output with the Glorys ocean reanalysis, on thirty one days in December twenty twenty four that the model never saw in training. In the upper thirty meters, the average error is zero point six to zero point nine degrees Celsius, with a correlation of up to zero point nine one. Deeper in the thermocline, the error grows, and we show that honestly.

### Scene 12: Taking the data further

**[SCREEN ACTION]:** Close the validation panel. Click "Download NetCDF (thetao)", then "Download NetCDF (derived layers)", and show the two downloaded files. Then hover over "Upload model output" without clicking.

**[NARRATION]:** Finally, the data does not stay locked inside the dashboard. Every day can be downloaded as a standard Net C D F file, together with a file of derived layers, including tropical cyclone heat potential. New model runs can be uploaded, and every file is checked before it appears.

### Scene 13: Closing

**[SCREEN ACTION]:** Set depth to 100 m, zoom out to the full basin, and hold on the map until the narration ends.

**[NARRATION]:** OceanEmbed turns satellite data we already collect into a clear view of the ocean below. It can support fishermen, help disaster managers track the heat that feeds cyclones, and give INCOIS a fast, open tool. We are Team Crisis Workers. Thank you for watching.

---

Narration word count: 711 (about 4 minutes 45 seconds to 5 minutes at a typical text-to-speech pace of 145 to 150 words per minute)
