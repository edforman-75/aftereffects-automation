#!/usr/bin/env python3
"""After Effects Automation Pipeline - Demo Visualization Tool"""

from modules.phase1.psd_parser import parse_psd
from modules.phase2.aepx_parser import parse_aepx
from modules.phase3.content_matcher import match_content_to_slots
from datetime import datetime


CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; }
.container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
.header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; text-align: center; }
.header h1 { font-size: 2.5em; margin-bottom: 10px; }
.section { padding: 40px; border-bottom: 1px solid #e0e0e0; }
.section h2 { color: #667eea; margin-bottom: 20px; font-size: 1.8em; border-left: 4px solid #667eea; padding-left: 15px; }
.info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }
.info-card { background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #667eea; }
.info-card h3 { color: #667eea; font-size: 0.9em; text-transform: uppercase; margin-bottom: 8px; }
.info-card p { font-size: 1.5em; font-weight: bold; }
.layer-item { padding: 12px; margin: 8px 0; background: #f8f9fa; border-radius: 6px; border-left: 4px solid #ddd; }
.layer-item.text { border-left-color: #4CAF50; }
.layer-item.image, .layer-item.smartobject { border-left-color: #2196F3; }
.badge { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 0.85em; font-weight: 600; color: white; }
.badge.text { background: #4CAF50; }
.badge.image, .badge.smartobject { background: #2196F3; }
.mapping { background: #f8f9fa; border-radius: 8px; padding: 20px; margin: 15px 0; border-left: 4px solid #ddd; }
.mapping.high { border-left-color: #4CAF50; }
.mapping.medium { border-left-color: #FFC107; }
.mapping.low { border-left-color: #F44336; }
.mapping-flow { display: flex; align-items: center; gap: 20px; margin: 15px 0; }
.mapping-flow > div { flex: 1; background: white; padding: 15px; border-radius: 6px; }
.mapping-flow .arrow { font-size: 2em; color: #667eea; flex: 0; }
.confidence { padding: 8px 16px; border-radius: 20px; font-weight: bold; }
.confidence.high { background: #4CAF50; color: white; }
.confidence.medium { background: #FFC107; color: #333; }
.confidence.low { background: #F44336; color: white; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
.stat-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px; text-align: center; }
.stat-card p { font-size: 3em; font-weight: bold; }
.text-content { color: #4CAF50; font-weight: 600; }
"""


def confidence_class(conf):
    """Get confidence class and label."""
    if conf >= 0.9:
        return "high", "High"
    elif conf >= 0.6:
        return "medium", "Medium"
    return "low", "Low"


def generate_psd_section(psd):
    """Generate PSD section HTML."""
    text_count = sum(1 for l in psd['layers'] if l['type'] == 'text')
    
    layers = ""
    for layer in psd['layers']:
        text_content = ""
        if layer['type'] == 'text' and 'text' in layer:
            text_content = f'<span class="text-content">"{layer["text"].get("content", "")}"</span>'
        
        layers += f"""<div class="layer-item {layer['type']}">
            <strong>{layer['name']}</strong> {text_content}
            <span class="badge {layer['type']}" style="float: right;">{layer['type']}</span>
        </div>"""
    
    return f"""<div class="section">
        <h2>📄 PSD Source Analysis</h2>
        <div class="info-grid">
            <div class="info-card"><h3>Document</h3><p>{psd['filename']}</p></div>
            <div class="info-card"><h3>Dimensions</h3><p>{psd['width']} × {psd['height']}</p></div>
            <div class="info-card"><h3>Total Layers</h3><p>{len(psd['layers'])}</p></div>
            <div class="info-card"><h3>Text Layers</h3><p>{text_count}</p></div>
        </div>
        <div>{layers}</div>
    </div>"""


def generate_aepx_section(aepx):
    """Generate AEPX section HTML."""
    main = next(c for c in aepx['compositions'] if c['name'] == aepx['composition_name'])
    
    placeholders = ""
    for ph in aepx['placeholders']:
        placeholders += f"""<div class="layer-item {ph['type']}">
            <strong>{ph['name']}</strong> <small>({ph['composition']})</small>
            <span class="badge {ph['type']}" style="float: right;">{ph['type']}</span>
        </div>"""
    
    return f"""<div class="section">
        <h2>🎬 AEPX Template Analysis</h2>
        <div class="info-grid">
            <div class="info-card"><h3>Template</h3><p>{aepx['filename']}</p></div>
            <div class="info-card"><h3>Composition</h3><p>{aepx['composition_name']}</p></div>
            <div class="info-card"><h3>Dimensions</h3><p>{main['width']} × {main['height']}</p></div>
            <div class="info-card"><h3>Placeholders</h3><p>{len(aepx['placeholders'])}</p></div>
        </div>
        <div>{placeholders}</div>
    </div>"""


def generate_mappings_section(mappings):
    """Generate mappings section HTML."""
    html = ""
    for i, m in enumerate(mappings['mappings'], 1):
        c_class, c_label = confidence_class(m['confidence'])
        html += f"""<div class="mapping {c_class}">
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <h3>Mapping #{i}</h3>
                <span class="confidence {c_class}">{c_label}: {m['confidence']*100:.0f}%</span>
            </div>
            <div class="mapping-flow">
                <div><small>PSD Layer</small><br><strong>{m['psd_layer']}</strong></div>
                <div class="arrow">→</div>
                <div><small>AEPX Placeholder</small><br><strong>{m['aepx_placeholder']}</strong></div>
            </div>
            <div style="color: #666; font-style: italic;">💡 {m['reason']}</div>
        </div>"""
    
    return f'<div class="section"><h2>🔗 Intelligent Mappings</h2>{html}</div>'


def generate_statistics_section(mappings, psd, aepx):
    """Generate statistics section HTML."""
    total = len(mappings['mappings'])
    high_conf = sum(1 for m in mappings['mappings'] if m['confidence'] >= 0.9)
    main_ph = [p for p in aepx['placeholders'] if p['composition'] == aepx['composition_name']]
    success_rate = (total / len(main_ph) * 100) if main_ph else 0
    
    unmapped = ""
    if mappings['unmapped_psd_layers']:
        items = "".join(f"<li>{l}</li>" for l in mappings['unmapped_psd_layers'])
        unmapped += f'<div style="background: #fff3e0; border-left: 4px solid #FF9800; padding: 20px; border-radius: 8px; margin-top: 20px;"><h3 style="color: #FF9800;">⚠️ Unmapped PSD Layers</h3><ul>{items}</ul></div>'
    
    if mappings['unfilled_placeholders']:
        items = "".join(f"<li>{p}</li>" for p in mappings['unfilled_placeholders'])
        unmapped += f'<div style="background: #fff3e0; border-left: 4px solid #FF9800; padding: 20px; border-radius: 8px; margin-top: 20px;"><h3 style="color: #FF9800;">⚠️ Unfilled Placeholders</h3><ul>{items}</ul></div>'
    
    return f"""<div class="section">
        <h2>📊 Summary Statistics</h2>
        <div class="stats-grid">
            <div class="stat-card"><h3>Total Mappings</h3><p>{total}</p></div>
            <div class="stat-card"><h3>High Confidence</h3><p>{high_conf}</p></div>
            <div class="stat-card"><h3>Success Rate</h3><p>{success_rate:.0f}%</p></div>
        </div>
        {unmapped}
    </div>"""


def generate_html(psd, aepx, mappings):
    """Generate complete HTML report."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>After Effects Automation Pipeline - Demo Report</title>
    <style>{CSS}</style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 After Effects Automation Pipeline</h1>
            <p style="font-size: 1.2em;">Proof of Concept - Intelligent Content Mapping</p>
            <p style="font-size: 0.9em; margin-top: 10px; opacity: 0.9;">Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        </div>
        {generate_psd_section(psd)}
        {generate_aepx_section(aepx)}
        {generate_mappings_section(mappings)}
        {generate_statistics_section(mappings, psd, aepx)}
        <div style="background: #f8f9fa; padding: 20px; text-align: center; color: #666; font-size: 0.9em;">
            Generated by After Effects Automation Pipeline (Modules 1.1, 2.1, 3.1)<br>
            🤖 Powered by Claude Code
        </div>
    </div>
</body>
</html>"""


def main():
    """Main execution."""
    print("=" * 70)
    print("After Effects Automation Pipeline - Demo Generator")
    print("=" * 70)
    
    print("\n📄 Loading PSD file...")
    psd = parse_psd('sample_files/test-photoshop-doc.psd')
    print(f"   ✓ Loaded: {psd['filename']}")
    
    print("\n🎬 Loading AEPX template...")
    aepx = parse_aepx('sample_files/test-after-effects-project.aepx')
    print(f"   ✓ Loaded: {aepx['filename']}")
    
    print("\n🔗 Running content matcher...")
    mappings = match_content_to_slots(psd, aepx)
    print(f"   ✓ Created {len(mappings['mappings'])} mappings")
    
    print("\n📝 Generating HTML report...")
    html = generate_html(psd, aepx, mappings)
    
    with open('demo_report.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("   ✓ Report saved to: demo_report.html")
    print("\n" + "=" * 70)
    print("✅ Demo report generated successfully!")
    print("=" * 70)
    print("\n🌐 Open demo_report.html in your browser to view the report\n")


if __name__ == "__main__":
    main()
