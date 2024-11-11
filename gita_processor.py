import pandas as pd
import random
from utils.text_processor import preprocess_text, calculate_similarity
from utils.monitoring import monitor
import streamlit as st
import logging

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
            
    def update_usage_stats(self, selected_verses):
        """Update verse and chapter usage statistics."""
        for _, verse in selected_verses.iterrows():
            verse_id = f"{verse['chapter']}.{verse['verse_number']}"
            chapter = verse['chapter']
            
            # Update verse usage count
            st.session_state.verse_usage[verse_id] = st.session_state.verse_usage.get(verse_id, 0) + 1
            
            # Update chapter usage count
            st.session_state.chapter_usage[chapter] = st.session_state.chapter_usage.get(chapter, 0) + 1
            
        # Log usage statistics
        monitor.log_performance_metric("verse_usage_distribution", 
            len(st.session_state.verse_usage), 
            {"context": "verse_tracking", "distribution": str(st.session_state.verse_usage)}
        )
        
        monitor.log_performance_metric("chapter_usage_distribution",
            len(st.session_state.chapter_usage),
            {"context": "chapter_tracking", "distribution": str(st.session_state.chapter_usage)}
        )
        
    def calculate_verse_score(self, similarity, verse_id, chapter):
        """Calculate final verse score with penalties and boosts."""
        base_score = similarity
        
        # Apply penalty for frequently used verses
        usage_count = st.session_state.verse_usage.get(verse_id, 0)
        penalty_factor = 1.0 / (1.0 + (0.2 * usage_count))  # Decrease score for frequently used verses
        
        # Apply penalty for verses used in last response
        if verse_id in st.session_state.last_verses:
            penalty_factor *= 0.5
            
        # Apply boost for underrepresented chapters
        chapter_usage = st.session_state.chapter_usage.get(chapter, 0)
        chapter_boost = 1.0 / (1.0 + (0.1 * chapter_usage))
        
        # Add small random factor for verses with similar scores
        randomization = random.uniform(0.95, 1.05)
        
        final_score = base_score * penalty_factor * chapter_boost * randomization
        
        # Log score components
        monitor.log_performance_metric("verse_scoring", final_score, {
            "context": "score_calculation",
            "verse_id": verse_id,
            "base_score": base_score,
            "penalty_factor": penalty_factor,
            "chapter_boost": chapter_boost,
            "randomization": randomization
        })
        
        return final_score
        
    def find_relevant_verses(self, question, top_n=5):
        """Find the most relevant verses for a given question with diversity and usage tracking."""
        try:
            processed_question = preprocess_text(question)
            
            # Calculate similarity scores with penalties and boosts
            verse_scores = []
            for idx, verse in enumerate(self.processed_verses):
                similarity = calculate_similarity(processed_question, verse)
                chapter = self.gita_df.iloc[idx]['chapter']
                verse_number = self.gita_df.iloc[idx]['verse_number']
                verse_id = f"{chapter}.{verse_number}"
                
                # Calculate final score with penalties and boosts
                final_score = self.calculate_verse_score(similarity, verse_id, chapter)
                
                verse_scores.append({
                    'index': idx,
                    'score': final_score,
                    'chapter': chapter,
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
            st.session_state.last_verses = {f"{verse['chapter']}.{verse['verse_number']}" 
                                          for _, verse in selected_df.iterrows()}
            
            # Log selection metrics
            monitor.log_performance_metric("verse_selection", {
                'verses_selected': len(selected_verses),
                'unique_chapters': len(selected_chapters),
                'average_score': sum(v['score'] for v in selected_verses) / len(selected_verses),
                'chapter_distribution': list(selected_chapters)
            }, {
                "context": "verse_selection",
                "question": question
            })
            
            return selected_df
            
        except Exception as e:
            monitor.log_error("system", e, {"context": "find_relevant_verses"})
            return pd.DataFrame(columns=self.gita_df.columns)
