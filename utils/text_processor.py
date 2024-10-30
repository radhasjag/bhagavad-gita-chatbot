import re
from typing import Text
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

def initialize_nltk():
    """Initialize NLTK by downloading required resources."""
    try:
        nltk.download('punkt')
        nltk.download('stopwords')
        nltk.download('wordnet')
        nltk.download('averaged_perceptron_tagger')
    except Exception as e:
        print(f"Warning: Failed to download NLTK data: {str(e)}")

# Initialize NLTK resources
initialize_nltk()

def preprocess_text(text: Text) -> Text:
    """Preprocess text for similarity matching."""
    try:
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters
        text = re.sub(r'[^a-zA-Z\s]', '', text)
        
        # Simple word splitting as fallback
        tokens = text.split()
        
        try:
            # Try NLTK tokenization
            tokens = word_tokenize(text)
            
            # Remove stopwords if available
            try:
                stop_words = set(stopwords.words('english'))
                tokens = [token for token in tokens if token not in stop_words]
            except:
                pass
            
            # Try lemmatization
            try:
                lemmatizer = WordNetLemmatizer()
                tokens = [lemmatizer.lemmatize(token) for token in tokens]
            except:
                pass
        except:
            pass
        
        return ' '.join(tokens)
    except Exception as e:
        print(f"Warning: Error in text preprocessing: {str(e)}")
        return text

def calculate_similarity(text1: Text, text2: Text) -> float:
    """Calculate similarity between two texts using Jaccard similarity."""
    try:
        set1 = set(text1.split())
        set2 = set(text2.split())
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union != 0 else 0
    except Exception as e:
        print(f"Warning: Error in similarity calculation: {str(e)}")
        return 0.0
