import re
from typing import Text
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet
from utils.monitoring import monitor

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

def get_wordnet_pos(word):
    """Map POS tag to first character lemmatize() accepts"""
    tag = nltk.pos_tag([word])[0][1][0].upper()
    tag_dict = {
        "J": wordnet.ADJ,
        "N": wordnet.NOUN,
        "V": wordnet.VERB,
        "R": wordnet.ADV
    }
    return tag_dict.get(tag, wordnet.NOUN)

def preprocess_text(text: Text) -> Text:
    """Preprocess text for similarity matching with enhanced semantic processing."""
    try:
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters
        text = re.sub(r'[^a-zA-Z\s]', '', text)
        
        try:
            # Enhanced tokenization with POS tagging
            tokens = word_tokenize(text)
            
            # Remove stopwords
            try:
                stop_words = set(stopwords.words('english'))
                tokens = [token for token in tokens if token not in stop_words]
            except:
                pass
            
            # Enhanced lemmatization with POS tagging
            try:
                lemmatizer = WordNetLemmatizer()
                tokens = [lemmatizer.lemmatize(token, get_wordnet_pos(token)) for token in tokens]
            except:
                pass
            
            return ' '.join(tokens)
        except:
            # Fallback to simple word splitting
            return ' '.join(text.split())
            
    except Exception as e:
        monitor.log_error("system", e, {"context": "preprocess_text"})
        return text

def calculate_similarity(text1: Text, text2: Text) -> float:
    """Calculate similarity between two texts using enhanced semantic matching."""
    try:
        # Convert texts to sets of words
        set1 = set(text1.split())
        set2 = set(text2.split())
        
        # Calculate basic Jaccard similarity
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        jaccard_sim = intersection / union if union != 0 else 0
        
        # Enhanced similarity with semantic relationships
        semantic_sim = 0.0
        try:
            # Calculate semantic similarity using WordNet
            lemmatizer = WordNetLemmatizer()
            words1 = [lemmatizer.lemmatize(word, get_wordnet_pos(word)) for word in set1]
            words2 = [lemmatizer.lemmatize(word, get_wordnet_pos(word)) for word in set2]
            
            # Count words with similar meanings
            semantic_matches = 0
            for word1 in words1:
                synsets1 = wordnet.synsets(word1)
                if not synsets1:
                    continue
                    
                for word2 in words2:
                    synsets2 = wordnet.synsets(word2)
                    if not synsets2:
                        continue
                        
                    # Check if words are semantically related
                    if any(s1.path_similarity(s2) and s1.path_similarity(s2) > 0.5 
                          for s1 in synsets1 for s2 in synsets2):
                        semantic_matches += 1
            
            semantic_sim = semantic_matches / max(len(words1), len(words2)) if words1 and words2 else 0
            
        except Exception as e:
            monitor.log_error("system", e, {"context": "semantic_similarity"})
        
        # Combine Jaccard and semantic similarity with weights
        final_similarity = (0.6 * jaccard_sim) + (0.4 * semantic_sim)
        
        # Log similarity metrics
        monitor.log_performance_metric("similarity_calculation", {
            'jaccard_similarity': jaccard_sim,
            'semantic_similarity': semantic_sim,
            'final_similarity': final_similarity
        }, {
            "context": "calculate_similarity"
        })
        
        return final_similarity
        
    except Exception as e:
        monitor.log_error("system", e, {"context": "calculate_similarity"})
        return 0.0
