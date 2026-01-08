import pandas as pd
import numpy as np
import joblib
import nltk
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Embedding, SpatialDropout1D
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
import os

# Download NLTK data
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)

def load_data():
    """Loads and preprocesses the training data."""
    print("Loading datasets...")
    df1 = pd.read_csv('dataset/Nazario_5.csv')
    df2 = pd.read_csv('dataset/email_text.csv')
    all_dfs = [df1, df2]

    df = pd.concat(all_dfs, ignore_index=True)
    df.dropna(subset=['text', 'label'], inplace=True)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    print(f"Training with a total of {len(df)} emails.")
    return df['text'].values, df['label'].values

def train_and_evaluate_lr(X_train, X_test, y_train, y_test):
    """Trains and evaluates the Logistic Regression model."""
    print("\n=== Training Logistic Regression Model ====")
    tfidf_vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
    X_train_tfidf = tfidf_vectorizer.fit_transform(X_train)
    X_test_tfidf = tfidf_vectorizer.transform(X_test)

    lr_model = LogisticRegression(random_state=42, max_iter=1000)
    lr_model.fit(X_train_tfidf, y_train)
    lr_score = lr_model.score(X_test_tfidf, y_test)
    print(f"Logistic Regression Accuracy: {lr_score:.4f}")
    return lr_model, tfidf_vectorizer, lr_score

def train_and_evaluate_rf(X_train_tfidf, X_test_tfidf, y_train, y_test):
    """Trains and evaluates the Random Forest model."""
    print("\n=== Training Random Forest Model ====")
    rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
    rf_model.fit(X_train_tfidf, y_train)
    rf_score = rf_model.score(X_test_tfidf, y_test)
    print(f"Random Forest Accuracy: {rf_score:.4f}")
    return rf_model, rf_score

def train_and_evaluate_lstm(X_train, X_test, y_train, y_test):
    """Trains and evaluates the LSTM model."""
    print("\n=== Training LSTM Model ====")
    max_words = 1000
    max_len = 100

    y_train = y_train.astype(int)
    y_test = y_test.astype(int)
    X_train = [str(text) for text in X_train]
    X_test = [str(text) for text in X_test]

    tokenizer = Tokenizer(num_words=max_words)
    tokenizer.fit_on_texts(X_train)
    X_train_seq = tokenizer.texts_to_sequences(X_train)
    X_test_seq = tokenizer.texts_to_sequences(X_test)

    X_train_pad = pad_sequences(X_train_seq, maxlen=max_len)
    X_test_pad = pad_sequences(X_test_seq, maxlen=max_len)

    lstm_model = Sequential()
    lstm_model.add(Embedding(max_words, 128, input_length=max_len))
    lstm_model.add(SpatialDropout1D(0.2))
    lstm_model.add(LSTM(64, dropout=0.2, recurrent_dropout=0.2))
    lstm_model.add(Dense(1, activation='sigmoid'))

    lstm_model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])
    lstm_model.fit(X_train_pad, y_train, epochs=5, batch_size=32, validation_split=0.1, verbose=1)

    lstm_score = lstm_model.evaluate(X_test_pad, y_test, verbose=0)[1]
    print(f"LSTM Accuracy: {lstm_score:.4f}")
    return lstm_model, tokenizer, lstm_score

def save_models(lr_model, rf_model, lstm_model, tfidf_vectorizer, tokenizer, scores):
    """Saves the trained models and tokenizers."""
    print("\n=== Saving Models ====")
    os.makedirs('models', exist_ok=True)
    joblib.dump(lr_model, 'models/lr_model.pkl')
    joblib.dump(rf_model, 'models/rf_model.pkl')
    joblib.dump(tfidf_vectorizer, 'models/tfidf_vectorizer.pkl')
    joblib.dump(tokenizer, 'models/tokenizer.pkl')
    lstm_model.save('models/lstm_model.h5')

    print("\nAll models saved successfully!")
    print(f"  - Logistic Regression: {scores['lr']:.4f}")
    print(f"  - Random Forest: {scores['rf']:.4f}")
    print(f"  - LSTM: {scores['lstm']:.4f}")

def main():
    """Main function to run the training pipeline."""
    X, y = load_data()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    lr_model, tfidf_vectorizer, lr_score = train_and_evaluate_lr(X_train, X_test, y_train, y_test)
    X_train_tfidf = tfidf_vectorizer.transform(X_train)
    X_test_tfidf = tfidf_vectorizer.transform(X_test)

    rf_model, rf_score = train_and_evaluate_rf(X_train_tfidf, X_test_tfidf, y_train, y_test)
    lstm_model, tokenizer, lstm_score = train_and_evaluate_lstm(X_train, X_test, y_train, y_test)

    scores = {'lr': lr_score, 'rf': rf_score, 'lstm': lstm_score}
    save_models(lr_model, rf_model, lstm_model, tfidf_vectorizer, tokenizer, scores)

if __name__ == "__main__":
    main()
