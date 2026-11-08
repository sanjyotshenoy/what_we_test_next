window.DATA = window.DATA || {};
window.DATA.ot2Results = {
  "source": "benchmark/step3_MIC_benchmark/candidates_step3/leaderboard.csv",
  "models": [
    {
      "name": "Kimi K3.1 Pro",
      "before": 68.3,
      "after": 68.3,
      "repairs": 0,
      "before_gate": "pass",
      "after_gate": "pass"
    },
    {
      "name": "DeepSeek V4.1 Flash 1017",
      "before": 0.0,
      "after": 64.5,
      "repairs": 1,
      "before_gate": "fail",
      "after_gate": "pass"
    },
    {
      "name": "GLM 5.3",
      "before": 0.0,
      "after": 51.0,
      "repairs": 2,
      "before_gate": "fail",
      "after_gate": "pass"
    },
    {
      "name": "GPT-OSS-120B",
      "before": 0.0,
      "after": 10.6,
      "repairs": 3,
      "before_gate": "fail",
      "after_gate": "pass"
    },
    {
      "name": "Nemotron 3 Super",
      "before": 0.0,
      "after": 0.0,
      "repairs": 3,
      "before_gate": "fail",
      "after_gate": "fail"
    }
  ]
};
