# PhishGuard - Phishing Email Detection System

PhishGuard is an AI-powered phishing detection system that uses a cascading machine learning approach to identify phishing emails with high accuracy.

## Features

- **Cascading ML Pipeline**: Three-stage detection system using Logistic Regression, Random Forest, and LSTM
- **Secure Authentication**: User authentication with Replit Auth
- **Real-time Detection**: Instant phishing analysis with confidence scores
- **Analysis History**: Track your past email analyses
- **Professional UI**: Clean, modern interface with responsive design

## How It Works

### Stage 1: Logistic Regression
Fast lexical pattern detection for obvious phishing indicators. Makes immediate decisions when confidence is high (>70%).

### Stage 2: Random Forest
Handles nonlinear patterns and ambiguous cases using ensemble learning with 100 decision trees.

### Stage 3: LSTM Neural Network
Deep contextual understanding for sophisticated phishing attempts using recurrent neural networks.

## Technology Stack

- **Backend**: Flask (Python)
- **Machine Learning**: scikit-learn, TensorFlow/Keras
- **NLP**: NLTK, TF-IDF Vectorization
- **Database**: PostgreSQL
- **Authentication**: Replit Auth (OAuth)

## Getting Started

1. Sign in with your account
2. Navigate to the "Detect" page
3. Paste your email content
4. Click "Analyze Email"
5. View the results with confidence score and model stage

## Model Performance

- Logistic Regression: 83.3% accuracy
- Random Forest: 83.3% accuracy
- LSTM: Trained for contextual understanding

## Security

- Secure authentication with OAuth
- Database-backed session storage
- No sensitive data exposure
- All predictions are logged for your review

## Future Enhancements

- Admin dashboard with analytics
- Batch email processing
- Enhanced evaluation metrics (Precision, Recall, F1, ROC-AUC)
- Multilingual support
- Transformer-based models (BERT)
