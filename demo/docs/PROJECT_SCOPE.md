# Project Ouroboros

The current state of the project is as follows. We are basically setting up a benchmark for automating scientific experiments. We have step 1, about background work which we haven't worked on, but right now it isn't essential to the functionality of steps 2 and 3, which is to do with OT2 execution.

The system is the following:
2. Given the set of molecular compounds, we then want to produce reasonable high-level and checkable experimental protocols. This would be done via templates of existing protocols and a knowledge base of guidelines. Protocols extracted from existing experiments would be then integrated to inform what parameters to use.
3. Once the protocol is generated, we then translate the protocol into instructions that a machine, specifically OpenTrons-2, can read and carry out.

This is the core pipeline. We may consider additional steps such as additional compute spent cleaning OT-2 instructions, or better selection of protocols. The primary goal is to produce the core pipeline from the existing separate pieces. It is possible that certain pieces might still move like the exact knowledge graph being used, but we can expect most of the design to be stable.
