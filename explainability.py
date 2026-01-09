"""
Model Explainability Module using SHAP and LIME
Provides interpretability for sepsis prediction model
"""

import numpy as np
import pandas as pd
import pickle
import json
import base64
import io
from io import BytesIO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import shap
import lime
import lime.lime_tabular
from sklearn.neural_network import MLPClassifier


class ModelExplainer:
    """Wrapper class for model explainability using SHAP and LIME"""
    
    def __init__(self, model_path='model.pkl', data_path='sepsis.csv'):
        """
        Initialize the explainer with model and training data
        
        Args:
            model_path: Path to the trained model pickle file
            data_path: Path to the training data CSV file
        """
        self.model = pickle.load(open(model_path, 'rb'))
        self.data = pd.read_csv(data_path)
        
        # Feature names - exactly 27 features
        self.feature_names = [
            'HR', 'O2Sat', 'Temp', 'SBP', 'MAP', 'DBP', 'Resp',
            'BaseExcess', 'HCO3', 'FiO2', 'PaCO2', 'SaO2', 'Creatinine',
            'Bilirubin_direct', 'Glucose', 'Lactate', 'Magnesium', 'Phosphate',
            'Bilirubin_total', 'Hgb', 'WBC', 'Fibrinogen', 'Platelets',
            'Age', 'Gender', 'HospAdmTime', 'ICULOS'
        ]
        
        # Prepare training data for explainers
        self.X_train = self.data[self.feature_names].values
        
        # Initialize LIME explainer
        self.lime_explainer = lime.lime_tabular.LimeTabularExplainer(
            self.X_train,
            feature_names=self.feature_names,
            class_names=['Low Risk', 'High Risk'],
            mode='classification',
            verbose=False
        )
        
        # Initialize SHAP explainer (using KernelExplainer for model-agnostic approach)
        print("Initializing SHAP explainer... (this may take a moment)")
        # Use a sample of data for SHAP background
        self.background_data = shap.sample(self.X_train, 100)
        self.shap_explainer = shap.KernelExplainer(
            self.model.predict_proba,
            self.background_data
        )
        print("SHAP explainer ready!")
    
    def get_lime_explanation(self, instance, num_features=10):
        """
        Get LIME explanation for a prediction
        
        Args:
            instance: Input features as numpy array
            num_features: Number of features to explain
            
        Returns:
            dict: LIME explanation with feature contributions
        """
        try:
            exp = self.lime_explainer.explain_instance(
                instance,
                self.model.predict_proba,
                num_features=num_features
            )
            
            # Extract explanation as list of tuples
            lime_exp = exp.as_list()
            
            # Format for JSON serialization
            explanation = {
                'method': 'LIME',
                'prediction_class': 'High Risk' if exp.predict_proba[1] > 0.5 else 'Low Risk',
                'confidence': float(max(exp.predict_proba)),
                'features': []
            }
            
            for feature_desc, weight in lime_exp:
                explanation['features'].append({
                    'feature': str(feature_desc),
                    'contribution': float(weight)
                })
            
            return explanation, exp
        except Exception as e:
            print(f"LIME explanation error: {str(e)}")
            return None, None
    
    def get_shap_explanation(self, instance):
        """
        Get SHAP explanation for a prediction
        
        Args:
            instance: Input features as numpy array (2D)
            
        Returns:
            dict: SHAP explanation with feature importance
        """
        try:
            shap_values = self.shap_explainer.shap_values(instance)
            
            # For binary classification, take the high-risk class values
            if isinstance(shap_values, list):
                shap_vals = shap_values[1]
            else:
                shap_vals = shap_values
            
            prediction = self.model.predict(instance)[0]
            
            explanation = {
                'method': 'SHAP',
                'prediction': 'High Risk of Sepsis' if prediction == 1 else 'Low Risk of Sepsis',
                'features': []
            }
            
            # Get feature importances sorted by absolute value
            feature_importance = list(zip(
                self.feature_names,
                shap_vals[0] if shap_vals.ndim > 1 else shap_vals
            ))
            feature_importance.sort(key=lambda x: abs(x[1]), reverse=True)
            
            for feature_name, importance in feature_importance[:10]:
                explanation['features'].append({
                    'feature': feature_name,
                    'shap_value': float(importance),
                    'direction': 'increases risk' if importance > 0 else 'decreases risk'
                })
            
            return explanation, shap_values
        except Exception as e:
            print(f"SHAP explanation error: {str(e)}")
            return None, None
    
    def create_lime_plot(self, exp):
        """
        Create a visualization of LIME explanation
        
        Args:
            exp: LIME explanation object
            
        Returns:
            str: Base64 encoded image
        """
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            fig.patch.set_facecolor('#0a0e27')
            ax.set_facecolor('#1a1f3a')
            
            # Get explanation data
            lime_exp = exp.as_list()
            features = [item[0] for item in lime_exp]
            values = [item[1] for item in lime_exp]
            
            # Create bar plot
            colors = ['#ffd700' if v > 0 else '#ff6b6b' for v in values]
            ax.barh(features, values, color=colors, edgecolor='#ffd700', linewidth=1.5)
            
            ax.set_xlabel('Contribution to Prediction', color='#ffd700', fontsize=12, fontweight='bold')
            ax.set_ylabel('Features', color='#ffd700', fontsize=12, fontweight='bold')
            ax.set_title('LIME: Local Feature Importance', color='#ffd700', fontsize=14, fontweight='bold')
            ax.tick_params(colors='#b0b0b0')
            ax.spines['bottom'].set_color('#ffd700')
            ax.spines['left'].set_color('#ffd700')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            plt.tight_layout()
            
            # Convert to base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', facecolor='#0a0e27', edgecolor='none')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            plt.close()
            
            return image_base64
        except Exception as e:
            print(f"LIME plot error: {str(e)}")
            return None
    
    def create_shap_plot(self, instance, shap_values):
        """
        Create a visualization of SHAP explanation
        
        Args:
            instance: Input features as numpy array
            shap_values: SHAP values from explainer
            
        Returns:
            str: Base64 encoded image
        """
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            fig.patch.set_facecolor('#0a0e27')
            ax.set_facecolor('#1a1f3a')
            
            # Get SHAP values for high-risk class
            if isinstance(shap_values, list):
                shap_vals = shap_values[1][0]
            else:
                shap_vals = shap_values[0]
            
            # Sort by absolute importance
            indices = np.argsort(np.abs(shap_vals))[-10:]
            
            features_plot = [self.feature_names[i] for i in indices]
            values_plot = shap_vals[indices]
            
            colors = ['#ffd700' if v > 0 else '#ff6b6b' for v in values_plot]
            ax.barh(features_plot, values_plot, color=colors, edgecolor='#ffd700', linewidth=1.5)
            
            ax.set_xlabel('SHAP Value (Impact on Prediction)', color='#ffd700', fontsize=12, fontweight='bold')
            ax.set_ylabel('Features', color='#ffd700', fontsize=12, fontweight='bold')
            ax.set_title('SHAP: Global Feature Importance', color='#ffd700', fontsize=14, fontweight='bold')
            ax.tick_params(colors='#b0b0b0')
            ax.spines['bottom'].set_color('#ffd700')
            ax.spines['left'].set_color('#ffd700')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            plt.tight_layout()
            
            # Convert to base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', facecolor='#0a0e27', edgecolor='none')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            plt.close()
            
            return image_base64
        except Exception as e:
            print(f"SHAP plot error: {str(e)}")
            return None


def format_explanation_html(lime_dict, shap_dict):
    """
    Format explanations into HTML for display
    
    Args:
        lime_dict: LIME explanation dictionary
        shap_dict: SHAP explanation dictionary
        
    Returns:
        str: HTML formatted explanation
    """
    html = '<div style="margin-top: 20px;">'
    
    if lime_dict:
        html += '''
        <div style="background: rgba(255, 215, 0, 0.08); border: 1px solid rgba(255, 215, 0, 0.2); 
                    border-radius: 10px; padding: 15px; margin-bottom: 15px;">
            <h5 style="color: #ffd700;">LIME Explanation (Local Interpretable Model-agnostic Explanations)</h5>
            <p><strong>Prediction:</strong> <span style="color: #ffd700;">{}</span></p>
            <p><strong>Confidence:</strong> <span style="color: #ffd700;">{:.2%}</span></p>
            <p><strong>Top Contributing Features:</strong></p>
            <ul style="color: #b0b0b0;">
        '''.format(lime_dict['prediction_class'], lime_dict['confidence'])
        
        for feature in lime_dict['features'][:5]:
            direction = "↑" if feature['contribution'] > 0 else "↓"
            html += '<li>{} {} ({:.4f})</li>'.format(
                direction, feature['feature'], feature['contribution']
            )
        
        html += '</ul></div>'
    
    if shap_dict:
        html += '''
        <div style="background: rgba(255, 215, 0, 0.08); border: 1px solid rgba(255, 215, 0, 0.2); 
                    border-radius: 10px; padding: 15px;">
            <h5 style="color: #ffd700;">SHAP Explanation (SHapley Additive exPlanations)</h5>
            <p><strong>Prediction:</strong> <span style="color: #ffd700;">{}</span></p>
            <p><strong>Most Influential Features:</strong></p>
            <ul style="color: #b0b0b0;">
        '''.format(shap_dict['prediction'])
        
        for feature in shap_dict['features'][:5]:
            direction = "↑" if feature['shap_value'] > 0 else "↓"
            html += '<li>{} {} - {} ({:.4f})</li>'.format(
                direction, feature['feature'], feature['direction'], 
                abs(feature['shap_value'])
            )
        
        html += '</ul></div>'
    
    html += '</div>'
    return html
