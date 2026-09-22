"""
OmniDoc AI - Styling & Design System
High-impact dark mode styling, dual-pane layout optimization, glassmorphic cards,
and red security guardrail alert styles for [DATA_MISSING].
"""

CUSTOM_CSS = """
<style>
/* Import Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* App background */
.stApp {
    background: radial-gradient(circle at 10% 10%, #0d1117 0%, #080a0f 100%);
    color: #e6edf3;
}

/* Header Banner */
.omnidoc-header {
    background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(13, 17, 23, 0.95) 100%);
    border: 1px solid rgba(56, 139, 253, 0.25);
    border-radius: 14px;
    padding: 20px 24px;
    margin-bottom: 24px;
    backdrop-filter: blur(12px);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.37);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.omnidoc-title {
    font-size: 26px;
    font-weight: 800;
    letter-spacing: -0.5px;
    background: linear-gradient(90deg, #58a6ff 0%, #a371f7 50%, #f778ba 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
}

.omnidoc-subtitle {
    font-size: 13px;
    color: #8b949e;
    margin-top: 4px;
    font-weight: 400;
}

.omnidoc-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(35, 134, 54, 0.2);
    border: 1px solid rgba(46, 160, 67, 0.4);
    color: #3fb950;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
}

/* Pane containers */
.pane-card {
    background: rgba(22, 27, 34, 0.7);
    border: 1px solid rgba(48, 54, 61, 0.7);
    border-radius: 12px;
    padding: 16px;
    height: 100%;
}

.pane-title {
    font-size: 15px;
    font-weight: 700;
    color: #c9d1d9;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 14px;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(48, 54, 61, 0.8);
}

/* Zero-Hallucination RED Security Banner */
.security-alert-box {
    background: linear-gradient(135deg, rgba(248, 81, 73, 0.15) 0%, rgba(218, 54, 51, 0.08) 100%);
    border: 1px solid #f85149;
    border-left: 5px solid #f85149;
    border-radius: 8px;
    padding: 16px 20px;
    margin: 14px 0;
    color: #ff7b72;
    animation: pulseBorder 2s infinite ease-in-out;
}

@keyframes pulseBorder {
    0% { box-shadow: 0 0 0 0 rgba(248, 81, 73, 0.4); }
    70% { box-shadow: 0 0 0 8px rgba(248, 81, 73, 0); }
    100% { box-shadow: 0 0 0 0 rgba(248, 81, 73, 0); }
}

.security-alert-title {
    font-size: 14px;
    font-weight: 800;
    letter-spacing: 0.6px;
    color: #ff7b72;
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
}

.security-alert-msg {
    font-size: 13px;
    line-height: 1.5;
    color: #f0f6fc;
}

/* Verified Answer Box */
.verified-answer-card {
    background: rgba(13, 17, 23, 0.6);
    border: 1px solid rgba(56, 139, 253, 0.3);
    border-left: 4px solid #58a6ff;
    border-radius: 8px;
    padding: 16px;
    margin: 12px 0;
}

.answer-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
}

.answer-tag {
    background: rgba(56, 139, 253, 0.15);
    color: #58a6ff;
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
}

/* Page preview badge */
.page-attribution-badge {
    background: rgba(163, 113, 247, 0.15);
    border: 1px solid rgba(163, 113, 247, 0.4);
    color: #d2a8ff;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

/* Image preview container */
.source-image-container {
    background: #0d1117;
    border: 1px solid rgba(56, 139, 253, 0.3);
    border-radius: 10px;
    padding: 8px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    text-align: center;
}

/* Voice input widget styling */
.voice-bar {
    background: rgba(22, 27, 34, 0.9);
    border: 1px dashed rgba(88, 166, 255, 0.4);
    border-radius: 10px;
    padding: 12px;
    text-align: center;
    margin-bottom: 12px;
}
</style>
"""
