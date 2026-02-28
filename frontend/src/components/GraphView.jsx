import { useRef, useEffect, useState, useCallback } from 'react';
import * as d3 from 'd3';

export default function GraphView({ graphData, onNodeClick, selectedNode }) {
    const svgRef = useRef();
    const containerRef = useRef();
    const simRef = useRef();
    const [edgeType, setEdgeType] = useState('all');
    const [zoomLevel, setZoomLevel] = useState(1);

    const getRiskColor = useCallback((score) => {
        if (score >= 51) return '#EF4444'; // Red
        if (score >= 31) return '#EAB308'; // Yellow
        return '#22C55E'; // Green
    }, []);

    useEffect(() => {
        if (!graphData?.nodes?.length) return;
        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove();

        const width = containerRef.current?.clientWidth || 900;
        const height = containerRef.current?.clientHeight || 700;

        const g = svg.append('g');

        // Zoom
        const zoom = d3.zoom()
            .scaleExtent([0.2, 5])
            .on('zoom', (e) => {
                g.attr('transform', e.transform);
                setZoomLevel(e.transform.k);
            });
        svg.call(zoom);

        // Filter edges
        let edges = graphData.edges || [];
        if (edgeType === 'transaction') edges = edges.filter(e => e.type !== 'DIRECTOR_LINK');
        else if (edgeType === 'director') edges = edges.filter(e => e.type === 'DIRECTOR_LINK');

        const nodeMap = new Map(graphData.nodes.map(n => [n.id, n]));
        const validEdges = edges.filter(e => nodeMap.has(e.source?.id || e.source) && nodeMap.has(e.target?.id || e.target));

        // Simulation
        const sim = d3.forceSimulation(graphData.nodes)
            .force('link', d3.forceLink(validEdges).id(d => d.id).distance(60))
            .force('charge', d3.forceManyBody().strength(-120))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide(12));
        simRef.current = sim;

        // Edges
        const link = g.append('g').selectAll('line')
            .data(validEdges).join('line')
            .attr('stroke', d => d.type === 'DIRECTOR_LINK' ? 'rgba(123, 97, 255, 0.4)' : 'rgba(255,255,255,0.04)')
            .attr('stroke-width', d => d.type === 'DIRECTOR_LINK' ? 1.2 : 0.5)
            .attr('stroke-dasharray', d => d.type === 'DIRECTOR_LINK' ? '4,3' : 'none');

        // Nodes
        const node = g.append('g').selectAll('circle')
            .data(graphData.nodes).join('circle')
            .attr('r', d => d.risk_score >= 51 ? 8 : d.risk_score >= 31 ? 6 : 4)
            .attr('fill', d => getRiskColor(d.risk_score || 0))
            .attr('stroke', d => d.id === selectedNode ? '#fff' : 'transparent')
            .attr('stroke-width', d => d.id === selectedNode ? 2.5 : 0)
            .attr('cursor', 'pointer')
            .on('click', (e, d) => onNodeClick(d))
            .call(d3.drag()
                .on('start', (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
                .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
                .on('end', (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; })
            );

        // Tooltip
        const tooltip = d3.select(containerRef.current).select('.graph-tooltip-el');

        node.on('mouseover', function (e, d) {
            d3.select(this)
                .transition().duration(200)
                .attr('r', (d.risk_score >= 51 ? 8 : d.risk_score >= 31 ? 6 : 4) * 1.3)
                .style('filter', `drop-shadow(0 4px 6px rgba(0,0,0,0.5)) drop-shadow(0 0 8px ${getRiskColor(d.risk_score)})`);

            tooltip.style('display', 'block')
                .style('left', (e.offsetX + 16) + 'px')
                .style('top', (e.offsetY - 10) + 'px')
                .html(`
          <div class="tt-name">${d.name || d.id}</div>
          <div class="tt-row"><span>Risk Score</span><span style="color:${getRiskColor(d.risk_score || 0)}">${(d.risk_score || 0).toFixed(1)}</span></div>
          <div class="tt-row"><span>Band</span><span>${d.risk_band || 'N/A'}</span></div>
          <div class="tt-row"><span>Industry</span><span>${d.industry || 'N/A'}</span></div>
        `);
        }).on('mouseout', function (e, d) {
            d3.select(this)
                .transition().duration(200)
                .attr('r', d.risk_score >= 51 ? 8 : d.risk_score >= 31 ? 6 : 4)
                .style('filter', 'none');

            tooltip.style('display', 'none');
        });

        // Remove old static glow 

        sim.on('tick', () => {
            link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
            node.attr('cx', d => d.x).attr('cy', d => d.y);
        });

        return () => sim.stop();
    }, [graphData, edgeType, selectedNode, getRiskColor, onNodeClick]);

    const handleZoom = (factor) => {
        const svg = d3.select(svgRef.current);
        svg.transition().duration(300).call(
            d3.zoom().scaleExtent([0.2, 5]).on('zoom', (e) => {
                svg.select('g').attr('transform', e.transform);
                setZoomLevel(e.transform.k);
            }).scaleTo, factor
        );
    };

    const handleReset = () => {
        const svg = d3.select(svgRef.current);
        svg.transition().duration(500).call(
            d3.zoom().scaleExtent([0.2, 5]).on('zoom', (e) => {
                svg.select('g').attr('transform', e.transform);
                setZoomLevel(e.transform.k);
            }).transform, d3.zoomIdentity
        );
    };

    return (
        <div className="graph-container" ref={containerRef}>
            {/* Controls */}
            <div className="graph-controls">
                <div className="control-group">
                    <button className="ctrl-btn" onClick={() => handleZoom(zoomLevel * 1.3)} title="Zoom In">+</button>
                    <button className="ctrl-btn" onClick={() => handleZoom(zoomLevel * 0.7)} title="Zoom Out">−</button>
                    <button className="ctrl-btn" onClick={handleReset} title="Reset View">⟲</button>
                </div>
                <div className="control-group edge-toggles">
                    <button className={`ctrl-btn ${edgeType === 'all' ? 'active' : ''}`} onClick={() => setEdgeType('all')}>All</button>
                    <button className={`ctrl-btn ${edgeType === 'transaction' ? 'active' : ''}`} onClick={() => setEdgeType('transaction')}>Txn</button>
                    <button className={`ctrl-btn ${edgeType === 'director' ? 'active' : ''}`} onClick={() => setEdgeType('director')}>Dir</button>
                </div>
            </div>

            <svg ref={svgRef} />
            <div className="graph-tooltip-el graph-tooltip" style={{ display: 'none' }} />

            {/* Legend */}
            <div className="graph-legend">
                {[
                    { label: 'Low', color: 'var(--risk-low)' },
                    { label: 'Medium', color: 'var(--risk-medium)' },
                    { label: 'High', color: 'var(--risk-high)' },
                    { label: 'Critical', color: 'var(--risk-critical)' },
                ].map(l => (
                    <div key={l.label} className="legend-item">
                        <div className="legend-dot" style={{ background: l.color }} />
                        <span>{l.label}</span>
                    </div>
                ))}
                <div className="legend-item">
                    <div style={{ width: 16, height: 2, background: 'var(--accent-purple)', borderRadius: 1 }} />
                    <span>Director</span>
                </div>
            </div>
        </div>
    );
}
