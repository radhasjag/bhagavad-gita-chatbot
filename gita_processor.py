import pandas as pd
import random
from utils.text_processor import preprocess_text, calculate_similarity
from utils.monitoring import monitor
import streamlit as st
import logging
from typing import Dict, Any, List

class GitaProcessor:
    def __init__(self):
        self.gita_df = pd.read_csv('data/bhagavad_gita.csv')
        self.processed_verses = self.gita_df['verse_text'].apply(preprocess_text)
        
        # Initialize verse usage tracking in session state
        if 'verse_usage' not in st.session_state:
            st.session_state.verse_usage = {}
        if 'last_verses' not in st.session_state:
            st.session_state.last_verses = set()
        if 'chapter_usage' not in st.session_state:
            st.session_state.chapter_usage = {}
            
    def _convert_to_native_types(self, obj: Any) -> Any:
        """Convert pandas and numpy types to Python native types."""
        if hasattr(obj, 'item'):
            return obj.item()
        elif isinstance(obj, dict):
            return {key: self._convert_to_native_types(value) for key, value in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._convert_to_native_types(item) for item in obj]
        return obj
            
    def update_usage_stats(self, selected_verses):
        """Update verse and chapter usage statistics."""
        for _, verse in selected_verses.iterrows():
            verse_id = f"{verse['chapter']}.{verse['verse_number']}"
            chapter = int(verse['chapter'])  # Convert to native int
            
            # Update verse usage count
            st.session_state.verse_usage[verse_id] = st.session_state.verse_usage.get(verse_id, 0) + 1
            
            # Update chapter usage count
            st.session_state.chapter_usage[chapter] = st.session_state.chapter_usage.get(chapter, 0) + 1
            
        # Convert metrics to native types before logging
        verse_usage = self._convert_to_native_types(st.session_state.verse_usage)
        chapter_usage = self._convert_to_native_types(st.session_state.chapter_usage)
            
        # Log usage statistics
        monitor.log_performance_metric(
            "verse_usage_distribution", 
            float(len(verse_usage)), 
            {"context": "verse_tracking", "distribution": str(verse_usage)}
        )
        
        monitor.log_performance_metric(
            "chapter_usage_distribution",
            float(len(chapter_usage)),
            {"context": "chapter_tracking", "distribution": str(chapter_usage)}
        )
        
    def calculate_verse_score(self, similarity: float, verse_id: str, chapter: int) -> float:
        """Calculate final verse score with penalties and boosts."""
        base_score = float(similarity)
        
        # Apply penalty for frequently used verses
        usage_count = float(st.session_state.verse_usage.get(verse_id, 0))
        penalty_factor = 1.0 / (1.0 + (0.2 * usage_count))
        
        # Apply penalty for verses used in last response
        if verse_id in st.session_state.last_verses:
            penalty_factor *= 0.5
            
        # Apply boost for underrepresented chapters
        chapter_usage = float(st.session_state.chapter_usage.get(chapter, 0))
        chapter_boost = 1.0 / (1.0 + (0.1 * chapter_usage))
        
        # Add small random factor for verses with similar scores
        randomization = random.uniform(0.95, 1.05)
        
        final_score = float(base_score * penalty_factor * chapter_boost * randomization)
        
        # Log score components with native types
        monitor.log_performance_metric("verse_scoring", final_score, {
            "context": "score_calculation",
            "verse_id": verse_id,
            "base_score": float(base_score),
            "penalty_factor": float(penalty_factor),
            "chapter_boost": float(chapter_boost),
            "randomization": float(randomization)
        })
        
        return final_score
        
    def find_relevant_verses(self, question: str, top_n: int = 5) -> pd.DataFrame:
        """Find the most relevant verses for a given question with diversity and usage tracking."""
        try:
            processed_question = preprocess_text(question)
            
            # Calculate similarity scores with penalties and boosts
            verse_scores = []
            for idx, verse in enumerate(self.processed_verses):
                similarity = calculate_similarity(processed_question, verse)
                chapter = int(self.gita_df.iloc[idx]['chapter'])
                verse_number = int(self.gita_df.iloc[idx]['verse_number'])
                verse_id = f"{chapter}.{verse_number}"
                
                # Calculate final score with penalties and boosts
                final_score = self.calculate_verse_score(similarity, verse_id, chapter)
                
                verse_scores.append({
                    'index': int(idx),
                    'score': float(final_score),
                    'chapter': int(chapter),
                    'verse_id': verse_id
                })
            
            # Sort by final score
            verse_scores.sort(key=lambda x: x['score'], reverse=True)
            
            # Select verses ensuring diversity
            selected_verses = []
            selected_chapters = set()
            remaining_verses = verse_scores.copy()
            
            # First, select verses from different chapters
            while len(selected_verses) < top_n and remaining_verses:
                for verse in remaining_verses[:]:
                    if verse['chapter'] not in selected_chapters:
                        selected_verses.append(verse)
                        selected_chapters.add(verse['chapter'])
                        remaining_verses.remove(verse)
                        if len(selected_verses) >= top_n:
                            break
                
                # If we still need more verses and have gone through all chapters
                if len(selected_verses) < top_n and remaining_verses:
                    next_verse = remaining_verses[0]
                    selected_verses.append(next_verse)
                    remaining_verses.remove(next_verse)
            
            # Get selected verses from dataframe
            selected_indices = [verse['index'] for verse in selected_verses]
            selected_df = self.gita_df.iloc[selected_indices]
            
            # Update usage statistics and tracking
            self.update_usage_stats(selected_df)
            
            # Update last verses set
            st.session_state.last_verses = {
                f"{int(verse['chapter'])}.{int(verse['verse_number'])}" 
                for _, verse in selected_df.iterrows()
            }
            
            # Prepare metrics with native types
            metrics = {
                'verses_selected': len(selected_verses),
                'unique_chapters': len(selected_chapters),
                'average_score': float(sum(v['score'] for v in selected_verses) / len(selected_verses)),
                'chapter_distribution': [int(ch) for ch in selected_chapters]
            }
            
            # Log selection metrics
            monitor.log_performance_metric("verse_selection", 
                float(metrics['verses_selected']), 
                {
                    "context": "verse_selection",
                    "question": question,
                    "metrics": metrics
                }
            )
            
            return selected_df
            
        except Exception as e:
            monitor.log_error("system", e, {"context": "find_relevant_verses"})
            return pd.DataFrame(columns=self.gita_df.columns)
