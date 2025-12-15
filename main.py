"""¿A3",
"""¿A3",
]

CSV_HEADERS = [
    "Gene",
    "PDB_ID",
    "Experimental_Method",
    "Resolution",
    "Organism",
    "Release_Date",
]

CSV_PATH = "~/Downloads/slc_structures.csv"

# Mock rows to scale dataset for demo
GENES = [f"SLC6A{i}" for i in range(1, 101)]  # 100 distinct genes

METHODS = [
    "ELECTRON MICROSCOPY",
    "X-RAY DIFFRACTION",
    
]

ORGANISMS = [
    "Homo sapiens",
    "Mus musculus",
    "Rattus norvegicus",
]

def random_pdb_id():
    return "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=4))

def random_resolution(method):
    if method == "ELECTRON MICROSCOPY":
        return round(random.uniform(2.8, 4.2), 2)
    return round(random.uniform(1.8, 3.0), 2)

start_date = date(2014, 1, 1)

# ------------------------------------------------------------
# Generate mock rows
# - Exclude scraped genes
# - Multiple PDB rows per gene
# ------------------------------------------------------------
SCRAPED_SET = set(SCRAPED_SLC_GENES)
MOCK_GENES = [g for g in GENES if g not in SCRAPED_SET]

MOCK_SLC_ROWS = []

current_day_offset = 0

for gene in MOCK_GENES:
    # Each gene has 1–4 solved structures
    num_structures = random.randint(1, 4)

    for _ in range(num_structures):
        method = random.choice(METHODS)
        resolution = random_resolution(method)
        organism = random.choice(ORGANISMS)

        release_date = (
            start_date + timedelta(days=current_day_offset)
        ).isoformat()

        current_day_offset += random.randint(20, 90)

        MOCK_SLC_ROWS.append(
            f"{gene},"
            f"{random_pdb_id()},"
            f"{method},"
            f"{resolution},"
            f"{organism},"
            f"{release_date}"
        )

# ------------------------------------------------------------
# Env validation
# ------------------------------------------------------------
def validate_required_env_vars():
    required = [
        "CUA_API_KEY",
        "CUA_SANDBOX_NAME",
        "ANTHROPIC_API_KEY",
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise ValueError(f"Missing env vars: {', '.join(missing)}")

# ------------------------------------------------------------
# Run exactly one task
# ------------------------------------------------------------
async def run_single_task(agent: ComputerAgent, task: str):
    history = [{"role": "user", "content": task}]
    async for result in agent.run(history, stream=False):
        for item in result.get("output", []):
            if item.get("type") == "message":
                for part in item.get("content", []):
                    if part.get("text"):
                        print(part["text"])

# ------------------------------------------------------------
# Main agent logic
# ------------------------------------------------------------
async def run_agent():
    print("\n=== SLC → RCSB → CSV Demo ===")

    try:
        computer = Computer(
            os_type="linux",
            api_key=os.getenv("CUA_API_KEY"),
            name=os.getenv("CUA_SANDBOX_NAME"),
            provider_type=VMProviderType.CLOUD,
        )

        agent = ComputerAgent(
            model="claude-sonnet-4-5-20250929",
            tools=[computer],
            only_n_most_recent_images=2,
            verbosity=logging.INFO,
            use_prompt_caching=False,
            max_trajectory_budget=0.6,
        )

        # ------------------------------------------------------------
        # STEP 1: Create CSV with headers
        # ------------------------------------------------------------
        create_csv_task = f"""
Open a terminal.

Create a CSV file at {CSV_PATH} with this exact header line:

{','.join(CSV_HEADERS)}

Use echo and > .

Do not explain.
Confirm once done.
"""
        await run_single_task(agent, create_csv_task)

        # ------------------------------------------------------------
        # STEP 2: Live scrape 2 SLC genes
        # ------------------------------------------------------------
        for gene in SCRAPED_SLC_GENES:
            print(f"\n=== Live scraping {gene} ===")

            scrape_task = f"""
Open Firefox and go to https://www.rcsb.org.

Search for gene {gene}.

Click the most relevant protein structure.

As soon as these values are visible on screen, STOP navigating:

- PDB_ID
- Experimental Method
- Resolution
- Organism
- Release Date

Immediately open a terminal and append ONE row using echo >> :

echo "{gene},PDB_ID_VALUE,EXPERIMENTAL_METHOD_VALUE,RESOLUTION_VALUE,ORGANISM_VALUE,RELEASE_DATE_VALUE" >> {CSV_PATH}

Rules:
- Replace VALUE placeholders with actual values
- If missing, use Not Found
- Do NOT scroll further
- Do NOT verify
- Do NOT explain

After appending, run:
tail -n 1 {CSV_PATH}
"""
            await run_single_task(agent, scrape_task)
            await asyncio.sleep(2)

        # ------------------------------------------------------------
        # STEP 3: Append mock rows (NO browsing)
        # ------------------------------------------------------------
        mock_rows_block = "\\n".join(MOCK_SLC_ROWS)

        mock_task = f"""
Open a terminal.

You are NOT scraping or browsing in this step.

Append the following pre-generated CSV rows to {CSV_PATH}
using echo >> exactly as written:

{mock_rows_block}

After appending, run:
wc -l {CSV_PATH}

Do not explain.
"""
        await run_single_task(agent, mock_task)

        dashboard_task = f"""
Open a terminal.

Create a new Python file called app.py in the home directory.

Write Python code into app.py with the following requirements.

Tech stack:
- Python
- streamlit
- pandas
- plotly (do NOT use altair or matplotlib)

Data:
- Load the CSV file from:
  {CSV_PATH}

App configuration:
- Page title: "SLC Structure Explorer"
- Page layout: wide
- Use a clean, research-dashboard style layout

Data handling rules:
- Parse Release_Date as datetime (errors coerced)
- Convert Resolution to numeric (errors coerced)
- Treat values like "Not Found" or empty strings as NaN
- Do not drop rows unless strictly necessary

Sidebar:
- Section title: "Filters"
- Multiselect filter for Gene (default: all)
- Multiselect filter for Experimental_Method (default: all)
- Display total number of structures after filtering

Main layout:
Use sections with clear headers.

Section 1: Data Table
- Display the filtered dataframe
- Enable column sorting
- Show at least the following columns:
  Gene, PDB_ID, Experimental_Method, Resolution, Organism, Release_Date

Section 2: Summary Metrics
- Show three KPI-style metrics:
  - Total structures
  - Number of unique genes
  - Median resolution (Å), ignoring NaNs

Section 3: Visualizations

Visualization A: Bar Chart
- Type: plotly bar chart
- X axis: Gene
- Y axis: count of PDB_ID
- Title: "Number of Structures per Gene"
- Use a qualitative color palette
- Sort bars descending

Visualization B: Scatter Plot
- Type: plotly scatter
- X axis: Release_Date
- Y axis: Resolution
- Color by Gene
- Hover should show:
  - Gene
  - PDB_ID
  - Experimental_Method
- Title: "Structure Resolution Over Time"
- Reverse Y axis so higher resolution (lower Å) appears higher

General rules:
- Use clear variable names
- Add brief inline comments only where helpful
- Do not include markdown text or explanations
- Do not run the app
- Do not print anything
- ONLY write valid Python code to app.py

After writing the file:
- Run the following command:
  sed -n '1,200p app.py
"""

        await run_single_task(agent, dashboard_task)

        print("\n✅ Demo complete. CSV contains scraped + mock data.")

    except Exception as e:
        logger.error(f"Agent failed: {e}")
        traceback.print_exc()
        raise

# ------------------------------------------------------------
# Entrypoint
# ------------------------------------------------------------
def main():
    try:
        load_dotenv_files()
        validate_required_env_vars()
        signal.signal(signal.SIGINT, handle_sigint)
        asyncio.run(run_agent())
    except Exception as e:
        print("Fatal error:", e)
        traceback.print_exc()

if __name__ == "__main__":
    main()
