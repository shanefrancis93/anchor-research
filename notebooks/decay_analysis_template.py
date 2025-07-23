#!/usr/bin/env python3
"""
Template for analyzing guardrail decay patterns from labeled conversations.
Convert to Jupyter notebook for interactive analysis.
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Any
from scipy import stats

# Configuration
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


def load_labeled_transcripts(directory: Path) -> List[Dict[str, Any]]:
    """Load all labeled transcripts from a directory."""
    transcripts = []
    for filepath in directory.glob("labeled_*.jsonl"):
        with open(filepath, 'r') as f:
            data = json.load(f)
            if 'manual_labels' in data and data['manual_labels']:
                transcripts.append(data)
    return transcripts


def extract_decay_metrics(transcripts: List[Dict]) -> pd.DataFrame:
    """Extract labeled metrics into a DataFrame for analysis."""
    rows = []
    
    for transcript in transcripts:
        scenario = transcript.get('scenario', 'unknown')
        model = transcript.get('model', 'unknown')
        branch = transcript.get('branch', 'unknown')
        
        for label in transcript['manual_labels']:
            row = {
                'scenario': scenario,
                'model': model,
                'branch': branch,
                'turn': label['turn'],
                'pushback': label['pushback'],
                'polarity': label['polarity'],
                'decay_severity': label['decay_severity'],
                'user_strategy': label.get('user_strategy', 'unknown'),
                'confidence': label.get('labeler_confidence', 1.0)
            }
            rows.append(row)
    
    return pd.DataFrame(rows)


def plot_decay_curves(df: pd.DataFrame, metric: str = 'pushback'):
    """Plot decay curves for different models/scenarios."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.ravel()
    
    # 1. Average decay by model
    ax = axes[0]
    for model in df['model'].unique():
        model_data = df[df['model'] == model]
        avg_by_turn = model_data.groupby('turn')[metric].mean()
        ax.plot(avg_by_turn.index, avg_by_turn.values, marker='o', label=model)
    ax.set_xlabel('Turn')
    ax.set_ylabel(f'Average {metric}')
    ax.set_title(f'{metric.capitalize()} Decay by Model')
    ax.legend()
    
    # 2. Decay by user strategy
    ax = axes[1]
    strategies = df['user_strategy'].value_counts().head(5).index
    for strategy in strategies:
        strategy_data = df[df['user_strategy'] == strategy]
        avg_by_turn = strategy_data.groupby('turn')[metric].mean()
        ax.plot(avg_by_turn.index, avg_by_turn.values, marker='s', label=strategy)
    ax.set_xlabel('Turn')
    ax.set_ylabel(f'Average {metric}')
    ax.set_title(f'{metric.capitalize()} by User Strategy')
    ax.legend()
    
    # 3. Individual conversation trajectories
    ax = axes[2]
    for (model, scenario), group in df.groupby(['model', 'scenario']):
        turns = group['turn'].values
        values = group[metric].values
        ax.plot(turns, values, alpha=0.3, label=f"{model[:10]}_{scenario[:10]}")
    ax.set_xlabel('Turn')
    ax.set_ylabel(metric.capitalize())
    ax.set_title('Individual Conversation Trajectories')
    
    # 4. Decay rate distribution
    ax = axes[3]
    decay_rates = []
    for (model, scenario), group in df.groupby(['model', 'scenario']):
        if len(group) > 1:
            # Calculate decay rate as slope
            slope, _ = np.polyfit(group['turn'], group[metric], 1)
            decay_rates.append({'model': model, 'rate': slope})
    
    if decay_rates:
        rate_df = pd.DataFrame(decay_rates)
        rate_df.boxplot(column='rate', by='model', ax=ax)
        ax.set_xlabel('Model')
        ax.set_ylabel(f'{metric.capitalize()} Decay Rate')
        ax.set_title('Decay Rate Distribution by Model')
    
    plt.tight_layout()
    return fig


def analyze_strategy_effectiveness(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze which strategies are most effective at inducing decay."""
    results = []
    
    for strategy in df['user_strategy'].unique():
        strategy_data = df[df['user_strategy'] == strategy]
        
        # Average pushback reduction
        early_turns = strategy_data[strategy_data['turn'] <= 2]['pushback'].mean()
        late_turns = strategy_data[strategy_data['turn'] >= 4]['pushback'].mean()
        pushback_reduction = early_turns - late_turns
        
        # Polarity shift
        early_polarity = strategy_data[strategy_data['turn'] <= 2]['polarity'].mean()
        late_polarity = strategy_data[strategy_data['turn'] >= 4]['polarity'].mean()
        polarity_shift = late_polarity - early_polarity
        
        # Decay severity distribution
        severe_decay_pct = (strategy_data['decay_severity'].isin(['medium', 'high']).sum() / 
                           len(strategy_data) * 100)
        
        results.append({
            'strategy': strategy,
            'n_uses': len(strategy_data),
            'pushback_reduction': pushback_reduction,
            'polarity_shift': polarity_shift,
            'severe_decay_pct': severe_decay_pct
        })
    
    return pd.DataFrame(results).sort_values('pushback_reduction', ascending=False)


def plot_heatmap_analysis(df: pd.DataFrame):
    """Create heatmap visualizations of decay patterns."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # 1. Model vs Strategy effectiveness
    pivot = df.pivot_table(
        values='pushback',
        index='model',
        columns='user_strategy',
        aggfunc='mean'
    )
    sns.heatmap(pivot, annot=True, fmt='.2f', cmap='RdYlBu_r', ax=axes[0])
    axes[0].set_title('Average Pushback by Model and Strategy')
    
    # 2. Turn progression heatmap
    pivot2 = df.pivot_table(
        values='pushback',
        index='model',
        columns='turn',
        aggfunc='mean'
    )
    sns.heatmap(pivot2, annot=True, fmt='.2f', cmap='RdYlBu_r', ax=axes[1])
    axes[1].set_title('Pushback Progression by Turn')
    
    plt.tight_layout()
    return fig


def statistical_analysis(df: pd.DataFrame):
    """Perform statistical tests on decay patterns."""
    print("Statistical Analysis of Guardrail Decay")
    print("="*50)
    
    # 1. Test if decay is significant
    print("\n1. Testing for significant decay across turns:")
    models = df['model'].unique()
    for model in models:
        model_data = df[df['model'] == model]
        early = model_data[model_data['turn'] <= 2]['pushback']
        late = model_data[model_data['turn'] >= 4]['pushback']
        
        if len(early) > 0 and len(late) > 0:
            t_stat, p_value = stats.ttest_ind(early, late)
            print(f"\n{model}:")
            print(f"  Early turns mean: {early.mean():.2f}")
            print(f"  Late turns mean: {late.mean():.2f}")
            print(f"  t-statistic: {t_stat:.3f}, p-value: {p_value:.4f}")
            if p_value < 0.05:
                print("  *** Significant decay detected ***")
    
    # 2. Compare models
    print("\n\n2. Comparing decay rates between models:")
    decay_rates_by_model = {}
    for model in models:
        model_data = df[df['model'] == model]
        rates = []
        for scenario in model_data['scenario'].unique():
            scenario_data = model_data[model_data['scenario'] == scenario]
            if len(scenario_data) > 1:
                slope, _ = np.polyfit(scenario_data['turn'], scenario_data['pushback'], 1)
                rates.append(slope)
        if rates:
            decay_rates_by_model[model] = rates
    
    if len(decay_rates_by_model) >= 2:
        f_stat, p_value = stats.f_oneway(*decay_rates_by_model.values())
        print(f"\nANOVA test for model differences:")
        print(f"F-statistic: {f_stat:.3f}, p-value: {p_value:.4f}")
    
    # 3. Strategy effectiveness
    print("\n\n3. Most effective decay strategies:")
    strategy_stats = analyze_strategy_effectiveness(df)
    print(strategy_stats.to_string())


def generate_report(df: pd.DataFrame, output_dir: Path):
    """Generate a comprehensive decay analysis report."""
    output_dir.mkdir(exist_ok=True)
    
    # Generate plots
    fig1 = plot_decay_curves(df, 'pushback')
    fig1.savefig(output_dir / 'pushback_decay_curves.png', dpi=300, bbox_inches='tight')
    
    fig2 = plot_decay_curves(df, 'polarity')
    fig2.savefig(output_dir / 'polarity_decay_curves.png', dpi=300, bbox_inches='tight')
    
    fig3 = plot_heatmap_analysis(df)
    fig3.savefig(output_dir / 'heatmap_analysis.png', dpi=300, bbox_inches='tight')
    
    # Generate text report
    with open(output_dir / 'decay_analysis_report.txt', 'w') as f:
        f.write("Guardrail Decay Analysis Report\n")
        f.write("="*50 + "\n\n")
        
        f.write(f"Total conversations analyzed: {df['scenario'].nunique()}\n")
        f.write(f"Total turns labeled: {len(df)}\n")
        f.write(f"Models evaluated: {', '.join(df['model'].unique())}\n\n")
        
        f.write("Key Findings:\n")
        f.write("-"*30 + "\n")
        
        # Average decay
        for model in df['model'].unique():
            model_data = df[df['model'] == model]
            early_pushback = model_data[model_data['turn'] <= 2]['pushback'].mean()
            late_pushback = model_data[model_data['turn'] >= 4]['pushback'].mean()
            decay = ((early_pushback - late_pushback) / early_pushback * 100) if early_pushback > 0 else 0
            f.write(f"\n{model}:\n")
            f.write(f"  Average pushback decay: {decay:.1f}%\n")
            f.write(f"  Early turns: {early_pushback:.2f}, Late turns: {late_pushback:.2f}\n")
    
    print(f"\nReport generated in: {output_dir}")


# Example usage
if __name__ == "__main__":
    # Load data
    transcript_dir = Path("outputs/latest/transcripts")
    transcripts = load_labeled_transcripts(transcript_dir)
    
    if not transcripts:
        print("No labeled transcripts found!")
        exit(1)
    
    # Extract metrics
    df = extract_decay_metrics(transcripts)
    print(f"Loaded {len(df)} labeled turns from {len(transcripts)} conversations")
    
    # Perform analysis
    statistical_analysis(df)
    
    # Generate visualizations and report
    output_dir = Path("analysis_output")
    generate_report(df, output_dir)
    
    plt.show()