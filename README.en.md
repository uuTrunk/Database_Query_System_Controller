# Database Query System - Controller (Pure Web UI)

The Controller repository has been entirely purified from its former PyWebIO logic, any underlying ML prediction backend structures, or local script rendering jobs. It exists entirely as an uncoupled **Vue 3 (Vite)** single-page portal.

## Mechanics and Dual-Service Polling

### Environment Setup (Conda)
For an expedited setup experience, we recommend using Conda to provision a dedicated python environment and installing the dependencies via `requirement.txt`:
```bash
# 1. Create a conda environment named "dqs" (Python 3.9)
conda create -n dqs python=3.9 -y

# 2. Activate the environment
conda activate dqs

# 3. Install the dependencies
pip install -r requirement.txt
```

- **Sole Responsibility**: Serves a highly interactive, responsive access point wrapper for generic login features, chat prompts, and loading or cascading chart displays.
- **Decoupled Linkage**: On any graphical chart emission triggered by a user, this repo inherently forks requests directly from the client's browser (through the `fetch API`):
  1. Requests port `8001` (Database_Query_System_Training), fetching analytical ML suggestions on the recommended quantity of parallel connection threads.
  2. Sequentially, the DOM broadcasts those concurrent hits towards parameter rendering functions positioned at port `8000` (Database_Query_System_Agent) to retrieve dynamic content/graphs properly.

## Running the Application
Being completely scrubbed of any Django/Python backend implementations, you strictly require standard JavaScript runtimes for operation:
```bash
cd Controller
npm install
npm run dev
```
After resolution, Vite fires a hot-reloading development UI normally mounted onto http://localhost:5173/ for the end users.
