import pandas as pd
from utils.text_processor import preprocess_text, calculate_similarity

class GitaProcessor:
    def __init__(self):
        self.gita_df = pd.read_csv('data/bhagavad_gita.csv')
        self.processed_verses = self.gita_df['verse_text'].apply(preprocess_text)
        
    def find_relevant_verses(self, question, top_n=3):
        """Find the most relevant verses for a given question."""
        processed_question = preprocess_text(question)
        
        # Calculate similarity scores
        similarities = self.processed_verses.apply(
            lambda x: calculate_similarity(processed_question, x)
        )
        
        # Get top matching verses
        top_indices = similarities.nlargest(top_n).index
        return self.gita_df.iloc[top_indices]
