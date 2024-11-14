import streamlit as st
import requests
import random
import pandas as pd
from datetime import datetime
from sklearn.linear_model import LinearRegression
import numpy as np

# API Key and URL for Spoonacular
API_KEY = 'a79012e4b3e1431e812d8b17bee3a4d7'
SPOONACULAR_URL = 'https://api.spoonacular.com/recipes/findByIngredients'

# Initialization of session state variables
if "inventory" not in st.session_state:
    st.session_state["inventory"] = {
        "Tomato": {"Quantity": 5, "Unit": "gram", "Price": 3.0},
        "Banana": {"Quantity": 3, "Unit": "gram", "Price": 5.0},
        "Onion": {"Quantity": 2, "Unit": "piece", "Price": 1.5},
        "Garlic": {"Quantity": 3, "Unit": "clove", "Price": 0.5},
        "Olive Oil": {"Quantity": 1, "Unit": "liter", "Price": 8.0},
    }

if "roommates" not in st.session_state:
    st.session_state["roommates"] = ["Bilbo", "Frodo", "Gandalf der Weise"]
if "selected_user" not in st.session_state:
    st.session_state["selected_user"] = None
if "recipe_suggestions" not in st.session_state:
    st.session_state["recipe_suggestions"] = []
if "recipe_links" not in st.session_state:
    st.session_state["recipe_links"] = {}
if "selected_recipe" not in st.session_state:
    st.session_state["selected_recipe"] = None
if "selected_recipe_link" not in st.session_state:
    st.session_state["selected_recipe_link"] = None
if "cooking_history" not in st.session_state:
    st.session_state["cooking_history"] = []
if "ml_model" not in st.session_state:
    st.session_state["ml_model"] = None
if "user_ratings_data" not in st.session_state:
    st.session_state["user_ratings_data"] = pd.DataFrame(columns=["Person", "Recipe", "Rating"])

# Initialize Machine Learning Model
def train_ml_model():
    df = st.session_state["user_ratings_data"]
    if len(df) > 1:  # Train model only if there are enough data points
        X = pd.get_dummies(df[["Person", "Recipe"]])
        y = df["Rating"]
        model = LinearRegression()
        model.fit(X, y)
        st.session_state["ml_model"] = model
        st.success("ML model trained successfully!")

# Function to predict rating
def predict_rating(user, recipe):
    model = st.session_state["ml_model"]
    if model:
        input_data = pd.DataFrame([[user, recipe]], columns=["Person", "Recipe"])
        input_data = pd.get_dummies(input_data)
        X = pd.get_dummies(st.session_state["user_ratings_data"][["Person", "Recipe"]])
        input_data = input_data.reindex(columns=X.columns, fill_value=0)
        predicted_rating = model.predict(input_data)[0]
        return round(predicted_rating, 1)
    return None

# Recipe suggestion function
def get_recipes_from_inventory(selected_ingredients=None):
    ingredients = selected_ingredients if selected_ingredients else list(st.session_state["inventory"].keys())
    if not ingredients:
        st.warning("Inventory is empty. Please add some items.")
        return [], {}
    
    params = {
        "ingredients": ",".join(ingredients),
        "number": 100,
        "ranking": 2,
        "apiKey": API_KEY
    }
    response = requests.get(SPOONACULAR_URL, params=params)
    
    if response.status_code == 200:
        recipes = response.json()
        recipe_titles = []
        recipe_links = {}
        random.shuffle(recipes)

        for recipe in recipes:
            missed_ingredients = recipe.get("missedIngredientCount", 0)
            if missed_ingredients <= 2:
                recipe_link = f"https://spoonacular.com/recipes/{recipe['title'].replace(' ', '-')}-{recipe['id']}"
                missed_ingredients_names = [item["name"] for item in recipe.get("missedIngredients", [])]
                recipe_titles.append(recipe['title'])
                recipe_links[recipe['title']] = {
                    "link": recipe_link,
                    "missed_ingredients": missed_ingredients_names
                }
                if len(recipe_titles) >= 3:
                    break
        return recipe_titles, recipe_links
    else:
        st.error("Error fetching recipes. Please check your API key.")
        return [], {}

# Rating function
def rate_recipe(recipe_title, recipe_link):
    st.subheader(f"Rate the recipe: {recipe_title}")
    st.write(f"**{recipe_title}**: ([View Recipe]({recipe_link}))")
    rating = st.slider("Rate with stars (1-5):", 1, 5, key=f"rating_{recipe_title}")
    
    if st.button("Submit rating"):
        user = st.session_state["selected_user"]
        if user:
            st.success(f"You have rated '{recipe_title}' with {rating} stars!")
            st.session_state["cooking_history"].append({
                "Person": user,
                "Recipe": recipe_title,
                "Rating": rating,
                "Link": recipe_link,
                "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            st.session_state["user_ratings_data"] = pd.concat([
                st.session_state["user_ratings_data"],
                pd.DataFrame([[user, recipe_title, rating]], columns=["Person", "Recipe", "Rating"])
            ], ignore_index=True)
            train_ml_model()
        else:
            st.warning("Please select a user first.")

# Main application flow
def recipepage():
    st.title("You think you can cook! Better take a recipe!")
    
    if st.session_state["roommates"]:
        selected_roommate = st.selectbox("Select the roommate:", st.session_state["roommates"])
        st.session_state["selected_user"] = selected_roommate
        
        st.subheader("Recipe search options")
        search_mode = st.radio("Choose a search mode:", ("Automatic (use all inventory)", "Custom (choose ingredients)"))
        
        with st.form("recipe_form"):
            selected_ingredients = st.multiselect("Select ingredients from inventory:", st.session_state["inventory"].keys()) if search_mode == "Custom (choose ingredients)" else None
            search_button = st.form_submit_button("Get recipe suggestions")
            
            if search_button:
                recipe_titles, recipe_links = get_recipes_from_inventory(selected_ingredients)
                st.session_state["recipe_suggestions"] = recipe_titles
                st.session_state["recipe_links"] = recipe_links

        if st.session_state["recipe_suggestions"]:
            selected_recipe = st.selectbox("Select a recipe to cook", ["Please choose..."] + st.session_state["recipe_suggestions"])
            if selected_recipe != "Please choose...":
                st.session_state["selected_recipe"] = selected_recipe
                st.session_state["selected_recipe_link"] = st.session_state["recipe_links"][selected_recipe]["link"]
                predicted_rating = predict_rating(st.session_state["selected_user"], selected_recipe)
                if predicted_rating:
                    st.write(f"Predicted rating for this recipe: {predicted_rating} stars")
                rate_recipe(st.session_state["selected_recipe"], st.session_state["selected_recipe_link"])

# Run the recipe page
recipepage()