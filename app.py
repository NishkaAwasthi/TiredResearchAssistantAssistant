import streamlit as st
import pandas as pd
import plotly.express as px

# Page configuration
st.set_page_config(
    page_title="SLC Structure Explorer",
    page_icon="🧬",
    layout="wide"
)

# Title and subtitle
st.title("SLC Structure Explorer")
st.caption("Explore structural characterization of SLC genes to identify well-studied targets and research gaps.")

# Load and clean data
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("slc_structures.csv")
        
        # Data hygiene
        # Drop rows where Gene is missing
        df = df.dropna(subset=["Gene"])
        
        # Convert Resolution to numeric (coerce errors to NaN)
        df["Resolution"] = pd.to_numeric(df["Resolution"], errors="coerce")
        
        # Convert Release_Date to datetime
        df["Release_Date"] = pd.to_datetime(df["Release_Date"], errors="coerce")
        
        return df
    except FileNotFoundError:
        st.error("Error: slc_structures.csv not found in the current directory.")
        st.stop()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.stop()

df = load_data()

# Sidebar filters
with st.sidebar:
    st.header("Filters")
    
    # Gene multiselect filter
    if "Gene" in df.columns:
        unique_genes = sorted(df["Gene"].dropna().unique())
        selected_genes = st.multiselect(
            "Gene",
            options=unique_genes,
            default=unique_genes
        )
    else:
        st.warning("Gene column not found in data")
        selected_genes = []
    
    # Method multiselect filter
    if "Method" in df.columns:
        unique_methods = sorted(df["Method"].dropna().unique())
        selected_methods = st.multiselect(
            "Method",
            options=unique_methods,
            default=unique_methods
        )
    else:
        st.warning("Method column not found in data")
        selected_methods = []
    
    # Checkbox: Show only genes with missing structures
    show_missing_only = st.checkbox("Show only genes with missing structures")

# Apply filters
filtered_df = df.copy()

if selected_genes:
    filtered_df = filtered_df[filtered_df["Gene"].isin(selected_genes)]
else:
    filtered_df = filtered_df[filtered_df["Gene"].isna()]

if selected_methods:
    filtered_df = filtered_df[filtered_df["Method"].isin(selected_methods)]
else:
    filtered_df = filtered_df[filtered_df["Method"].isna()]

# Apply missing structures filter
if show_missing_only:
    filtered_df = filtered_df[
        (filtered_df["PDB_ID"].isna()) | 
        (filtered_df["PDB_ID"].astype(str).str.strip() == "Not Found")
    ]

# Calculate insights
total_genes = filtered_df["Gene"].nunique() if "Gene" in filtered_df.columns else 0
genes_with_structures = filtered_df[
    filtered_df["PDB_ID"].notna() & 
    (filtered_df["PDB_ID"].astype(str).str.strip() != "Not Found")
]["Gene"].nunique() if "PDB_ID" in filtered_df.columns else 0
genes_with_zero_structures = total_genes - genes_with_structures
total_pdb_structures = len(filtered_df[
    filtered_df["PDB_ID"].notna() & 
    (filtered_df["PDB_ID"].astype(str).str.strip() != "Not Found")
]) if "PDB_ID" in filtered_df.columns else 0

# Insight callouts
st.header("Insights")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Genes", total_genes)
col2.metric("Genes with at least one structure", genes_with_structures)
col3.metric("Genes with zero structures", genes_with_zero_structures)
col4.metric("Total PDB Structures", total_pdb_structures)

# Data Table section
st.header("Data Table")

# Create PDB_Link column
display_df = filtered_df.copy()
if "PDB_ID" in display_df.columns:
    def create_pdb_link(pdb_id):
        if pd.isna(pdb_id) or str(pdb_id).strip() == "Not Found":
            return "N/A"
        else:
            return f"https://www.rcsb.org/structure/{pdb_id}"
    
    display_df["PDB_Link"] = display_df["PDB_ID"].apply(create_pdb_link)

# Display sortable table
st.dataframe(display_df, use_container_width=True, hide_index=True)

# Visualizations section
st.header("Visualizations")

# Bar chart: Gene vs number of PDB structures
st.subheader("Number of PDB Structures per Gene")
if "Gene" in filtered_df.columns and "PDB_ID" in filtered_df.columns:
    # Exclude rows with missing PDB_ID
    bar_df = filtered_df[
        filtered_df["PDB_ID"].notna() & 
        (filtered_df["PDB_ID"].astype(str).str.strip() != "Not Found")
    ].copy()
    
    if len(bar_df) > 0:
        gene_counts = bar_df.groupby("Gene")["PDB_ID"].count().reset_index()
        gene_counts.columns = ["Gene", "Count"]
        gene_counts = gene_counts.sort_values("Count", ascending=False)
        
        fig_bar = px.bar(
            gene_counts,
            x="Gene",
            y="Count",
            labels={"Count": "Number of PDB Structures", "Gene": "Gene"},
            color="Count",
            color_continuous_scale="viridis"
        )
        fig_bar.update_layout(
            xaxis_title="Gene",
            yaxis_title="Number of PDB Structures",
            showlegend=False,
            height=500
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.warning("No structures found for bar chart")
else:
    st.warning("Required columns (Gene, PDB_ID) not found for bar chart")

# Scatter plot: Resolution vs Release_Date
st.subheader("Resolution vs Release Date")
if "Resolution" in filtered_df.columns and "Release_Date" in filtered_df.columns:
    scatter_df = filtered_df.copy()
    
    # Remove rows with missing values
    scatter_df = scatter_df.dropna(subset=["Resolution", "Release_Date"])
    
    if len(scatter_df) > 0:
        # Prepare hover data - include all required fields
        hover_data_list = []
        if "PDB_ID" in scatter_df.columns:
            hover_data_list.append("PDB_ID")
        if "Method" in scatter_df.columns:
            hover_data_list.append("Method")
        if "Organism" in scatter_df.columns:
            hover_data_list.append("Organism")
        
        fig_scatter = px.scatter(
            scatter_df,
            x="Release_Date",
            y="Resolution",
            color="Gene" if "Gene" in scatter_df.columns else None,
            labels={"Resolution": "Resolution (Å)", "Release_Date": "Release Date"},
            hover_data=hover_data_list if hover_data_list else None
        )
        fig_scatter.update_layout(
            xaxis_title="Release Date",
            yaxis_title="Resolution (Å)",
            height=500
        )
        # Reverse y-axis so lower resolution (better) is at top
        fig_scatter.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.warning("No valid data points for scatter plot (missing Resolution or Release_Date values)")
else:
    st.warning("Required columns (Resolution, Release_Date) not found for scatter plot")
