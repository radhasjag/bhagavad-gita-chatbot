import pandas as pd
from utils.text_processor import preprocess_text, calculate_similarity
from utils.monitoring import monitor
import logging

class GitaProcessor:
    def __init__(self):
        self.gita_df = pd.read_csv('data/bhagavad_gita.csv')
        self.processed_verses = self.gita_df['verse_text'].apply(preprocess_text)
        
    def find_relevant_verses(self, question, top_n=5):
        """Find the most relevant verses for a given question with chapter diversity."""
        try:
            processed_question = preprocess_text(question)
            
            # Calculate similarity scores with monitoring
            similarities = []
            for idx, verse in enumerate(self.processed_verses):
                similarity = calculate_similarity(processed_question, verse)
                similarities.append({
                    'index': idx,
                    'similarity': similarity,
                    'chapter': self.gita_df.iloc[idx]['chapter']
                })
            
            # Sort by similarity score
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Implement chapter diversity
            selected_verses = []
            selected_chapters = set()
            remaining_verses = similarities.copy()
            
            # First, select verses with highest similarity from different chapters
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
                    # Add the next highest similarity verse regardless of chapter
                    next_verse = remaining_verses[0]
                    selected_verses.append(next_verse)
                    remaining_verses.remove(next_verse)
            
            # Log verse selection metrics
            monitor.log_performance_metric("verse_selection", {
                'verses_selected': len(selected_verses),
                'unique_chapters': len(selected_chapters),
                'similarity_scores': [v['similarity'] for v in selected_verses],
                'chapter_distribution': list(selected_chapters)
            }, {
                "context": "verse_selection",
                "question": question
            })
            
            # Get final selected verse indices
            selected_indices = [verse['index'] for verse in selected_verses]
            
            return self.gita_df.iloc[selected_indices]
            
        except Exception as e:
            monitor.log_error("system", e, {"context": "find_relevant_verses"})
            # Return empty DataFrame with same columns as gita_df
            return pd.DataFrame(columns=self.gita_df.columns)
