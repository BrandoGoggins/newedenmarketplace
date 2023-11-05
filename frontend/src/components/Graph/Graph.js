import React from 'react';
import Plot from 'react-plotly.js';

function Graph({ data, itemName }) {
  
  const lineTrace = {
    x: data.map(d => d.date),
    y: data.map(d => d.average),
    type: 'scatter',
    mode: 'lines',
    name: 'Average Price',
    line: { color: 'orange' }
  };

  const barTrace = {
    x: data.map(d => d.date),
    y: data.map(d => d.volume),
    type: 'bar',
    name: 'Volume',
    yaxis: 'y2',
    marker: { color: '#00daff' },
    // visible: false
  };


  return (
    <Plot
      data={[lineTrace, barTrace]}
      layout={{
        autosize: true,
        plot_bgcolor: "transparent",
        paper_bgcolor: "transparent",
        legend: {
          font: {
            color: 'white' // This sets the legend text color to white
        }
      },
        title: {
          text: itemName,
          font: {
            color: 'white' // set main title color
          }
        },
        xaxis: {
          title: 'Date',
          color: 'white',
          tickcolor: 'white',
          gridcolor: 'gray',
          rangeslider: { bgcolor: 'gray', thickness: 0.15 },
          rangeselector: {
            buttons: [
              { count: 1, label: '1m', step: 'month', stepmode: 'backward' },
              { count: 6, label: '6m', step: 'month', stepmode: 'backward' },
              { count: 1, label: '1y', step: 'year', stepmode: 'backward' },
              { step: 'all' }
            ]
          }
        },
        yaxis: {
          title: 'Price [ISK]',
          color: 'white',
          tickcolor: 'white',
          gridcolor: 'gray'
        },
        yaxis2: {
          title: 'Volume',
          color: 'white',
          overlaying: 'y',
          side: 'right'
        },
        // updatemenus: updatemenus
      }}
      style={{ width: "100%", height: "100%" }}
      useResizeHandler={true}
    />
  );
}

export default Graph;
