# Sycophancy-Checker Development Roadmap

## Phase 1: Foundation (Week 1)
**Goal:** Basic infrastructure and single-model testing

### Day 1-2: Project Setup
- [x] Create project structure and folders
- [x] Set up configuration files (providers.yaml, settings.yaml)
- [x] Create .env.example and requirements.txt
- [x] Initialize git repository

### Day 3-4: Core Components
- [ ] Implement base ChatDriver interface
- [ ] Create OpenAI driver with async support
- [ ] Build scenario parser for markdown format
- [ ] Add basic logging infrastructure

### Day 5-7: Basic Runner
- [ ] Implement sequential turn execution
- [ ] Add single-branch conversation support
- [ ] Create CSV output module
- [ ] Test with one hardcoded scenario

## Phase 2: Multi-Model Support (Week 2)
**Goal:** Parallel model testing and evaluation

### Day 8-9: Additional Drivers
- [ ] Implement Anthropic driver
- [ ] Add driver factory pattern
- [ ] Test multi-model parallel execution

### Day 10-11: Evaluation Framework
- [ ] Create pushback evaluator (heuristic-based)
- [ ] Implement anchor drift metrics (polarity, embeddings)
- [ ] Add entropy calculation for OpenAI

### Day 12-14: Fork/Branch Logic
- [ ] Implement conversation forking
- [ ] Add transient anchor probe mechanism
- [ ] Ensure baseline isolation from anchor text

## Phase 3: Production Features (Week 3)
**Goal:** Robustness and usability

### Day 15-16: Batch Processing
- [ ] Create run_batch.py CLI script
- [ ] Add progress tracking and error handling
- [ ] Implement budget monitoring

### Day 17-18: Testing Infrastructure
- [ ] Write unit tests for core components
- [ ] Create gold set for evaluator validation
- [ ] Add integration tests

### Day 19-21: Documentation & Polish
- [ ] Write comprehensive README
- [ ] Add usage examples
- [ ] Create initial scenario library
- [ ] Set up GitHub Actions CI

## Phase 4: Analysis Tools (Week 4+)
**Goal:** Research-ready platform

### Week 4: Data Analysis
- [ ] Create analysis notebooks
- [ ] Build visualization scripts
- [ ] Generate first research charts

### Future Enhancements
- [ ] Streamlit dashboard
- [ ] Meta-model evaluator
- [ ] Local model support
- [ ] Advanced drift metrics

## Success Criteria
- [ ] ≤1000 LOC core implementation
- [ ] <10 minute setup for new users
- [ ] Reproducible results across runs
- [ ] Support for OpenAI + Anthropic APIs
- [ ] Automated evaluation pipeline

## Dependencies
- Python 3.9+
- asyncio for parallel execution
- pandas for data manipulation
- OpenAI/Anthropic Python SDKs
- PyYAML for configuration

## Risk Mitigation
1. **API Rate Limits:** Implement exponential backoff
2. **Token Costs:** Budget monitoring with hard stops
3. **Model Updates:** Pin specific model versions
4. **Data Loss:** Auto-save transcripts after each turn