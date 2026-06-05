#!/bin/bash
# 📊 EVOLUTION STATUS CHECKER
# Δείχνει το current score και evolution metrics

SWARM_DIR="/root/.openclaw/workspace/swarm_general"
LOG_DIR="$SWARM_DIR/logs"

echo ""
echo "🧬 SWARM EVOLUTION STATUS"
echo "========================"
echo ""

# Check if evolution engine is running
if pgrep -f "evolution_engine.py" > /dev/null; then
    echo "🟢 Evolution Engine: RUNNING"
else
    echo "🔴 Evolution Engine: STOPPED"
    echo "   Run: ./start_evolution.sh"
    exit 1
fi

# Load state if available
STATE_FILE="$SWARM_DIR/data/evolution_state.json"
if [ -f "$STATE_FILE" ]; then
    echo ""
    echo "📊 Evolution Metrics:"
    echo "-------------------"
    
    # Parse with python3
    python3 -c "
import json

try:
    with open('$STATE_FILE', 'r') as f:
        state = json.load(f)
    
    print(f\"  Generation: {state.get('generation', 0)}\")
    print(f\"  Current Score: {state.get('current_score', 0):.2f}/10\")
    print(f\"  Target Score: {state.get('target_score', 0)}/10\")
    print(f\"  Gap: {state.get('target_score', 0) - state.get('current_score', 0):.2f}\")
    print()
    
    improvements = state.get('improvements', [])
    applied = [i for i in improvements if i.get('status') == 'applied']
    print(f\"  Improvements Applied: {len(applied)}\")
    print(f\"  Bottlenecks Active: {len(state.get('bottlenecks', []))}\")
    print(f\"  Patterns Learned: {len(state.get('patterns', {}))}\")
    print()
    
    # Component scores
    scores = state.get('component_scores', {})
    print('  Component Breakdown:')
    for name, data in scores.items():
        status = '✅' if data['current'] >= data['target'] else '🔧'
        print(f\"    {status} {name}: {data['current']:.1f}/{data['target']:.1f}\")
    
    # Recent history
    history = state.get('evolution_history', [])
    if len(history) >= 2:
        print()
        print(f\"  Evolution History: {len(history)} cycles\")
        latest = history[-1]
        prev = history[-2]
        trend = latest['score'] - prev['score']
        if trend > 0:
            print(f\"    Trend: 📈 +{trend:.2f} (improving)\")
        elif trend < 0:
            print(f\"    Trend: 📉 {trend:.2f} (declining)\")
        else:
            print(f\"    Trend: ➡️ stable\")
    
    # Score grade
    score = state.get('current_score', 0)
    print()
    if score >= 9.0:
        print(f\"  Grade: 🔥🔥🔥 S-TIER (9-10/10) 🎉\")
    elif score >= 8.0:
        print(f\"  Grade: 🔥🔥 A-TIER (8-9/10)\")
    elif score >= 7.0:
        print(f\"  Grade: 🔥 B-TIER (7-8/10)\")
    else:
        print(f\"  Grade: ⚡ C-TIER or below\")
        
except Exception as e:
    print(f\"Error reading state: {e}\")
"
else
    echo "📁 No state file yet - engine just started"
fi

echo ""
echo "📈 Live Log:"
echo "   tail -f $LOG_DIR/evolution.log"
echo ""
echo "========================"
