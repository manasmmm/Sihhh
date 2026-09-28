Hello, we are Team Crisis Workers, and this is OceanEmbed, our solution for Smart India Hackathon problem statement S I H two six zero six six. Satellites give us a picture of the ocean surface every day. But just a few hundred meters below, the temperature decides where fish gather, how strong a cyclone can grow, and how the monsoon behaves. Measuring it directly needs ships and floats, and they are few and far apart. OceanEmbed fills that gap.

At its heart is a graph neural network, supported by an X G Boost stage. The model looks back over thirty days of seven satellite measurements: sea surface temperature, salinity, sea surface height, currents and winds. It treats the ocean as a connected network, where each point learns from its neighbours in space and in depth. The result is temperature at fifteen depths, down to one thousand meters, on a zero point two five degree grid.

Let us open the dashboard. The header shows the date of the product and how long it stays valid. The green badge confirms that everything on screen comes from our trained model.

We begin at the surface. Bright colours show warm water, and darker colours show cooler water. The colour scale adapts to each depth, so small differences stand out. For a fair comparison, it can also be fixed from zero to thirty two degrees Celsius.

Now let us go below the surface. The depth rail takes us through all fifteen levels. At fifty meters, the pattern still resembles the surface. By one hundred meters, it changes completely, as we enter the thermocline, where temperature falls quickly with depth. This is the ocean that satellites cannot see.

The ocean is never still. You can step through the days one by one, or press play and watch it evolve at three speeds, as eddies drift and warm pools grow and shrink.

To understand a single place, simply click on it. The inspection card shows the temperature at the chosen depth, and a time series across every day, with its minimum, median and maximum. Below it is the full vertical profile, from the surface to one thousand meters.

Two lines on the profile carry special meaning. The yellow line is the mixed layer, the upper water stirred by the wind. The pink line is the warm layer depth, where the water cools to twenty degrees Celsius, a widely used marker of the thermocline. You can compare up to four locations side by side, and export each one.

OceanEmbed also goes beyond temperature. The layer menu turns each day into maps of ocean structure. They show where the thermocline sits, how deep the upper ocean is mixed, and where sharp fronts separate different water masses. Such fronts are often rich in nutrients. We show them at the surface, at fifty meters and at one hundred meters. One layer even reveals fronts that exist below the surface but are invisible from space.

Stepping back, the basin mean chart tracks the average temperature of the whole region over time. The Argo layer marks Argo floats, robotic instruments that measure real temperature profiles as they drift. And you can choose from five background maps, and adjust how strongly the data is shown.

A reconstruction is only useful if it can be trusted. The validation panel compares our output with the Glorys ocean reanalysis, on thirty one days in December twenty twenty four that the model never saw in training. In the upper thirty meters, the typical error is zero point seven to zero point nine degrees Celsius, with a correlation of up to zero point eight seven. Deeper in the thermocline, the error grows, and we show that honestly.

Finally, the data does not stay locked inside the dashboard. Every day can be downloaded as a standard Net C D F file, together with a file of derived layers, including tropical cyclone heat potential. New model runs can be uploaded, and every file is checked before it appears.

OceanEmbed turns satellite data we already collect into a clear view of the ocean below. It can support fishermen, help disaster managers track the heat that feeds cyclones, and give INCOIS a fast, open tool. We are Team Crisis Workers. Thank you for watching.
