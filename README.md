# power-attack
A framework for modeling and simulating attacks in power systems

## Getting Started

### Installing
* Clone repo
* Build Images Locally from repo root
    * `docker build -f docker/dockerfile.base -t edu.vanderbilt.isis/power-attack:base .`
    * `docker build -f docker/dockerfile -t edu.vanderbilt.isis/power-attack:latest .`

### Running
* Execute the following from repo root
    * `docker run --rm -it --name power_attack_test  edu.vanderbilt.isis/power-attack:latest `
