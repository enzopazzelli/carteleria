/* GENERADO POR scripts/vendorizar.mjs — NO EDITAR A MANO.
 *
 * Origen : https://github.com/deepnest-next/deepnest.git
 * Archivo: main/deepnest.js
 * Commit : 4d8b57f85ffc1831069549e3555eb7d97c408967
 * Licencia: MIT (ver vendor/LICENSE-deepnest.txt)
 *
 * Solo la clase GeneticAlgorithm (el resto del archivo es importación SVG
 * acoplada al DOM). Único cambio funcional: los 6 usos de
 * `Math.random()` pasan a un PRNG inyectable, para que el motor sea
 * reproducible — ver docs/PLAN-MOTOR-NESTING-DEEPNEST.md §5.
 *
 * Para actualizar: npm run vendorizar
 */
'use strict';

module.exports = function crearAlgoritmoGenetico(aleatorio) {

class GeneticAlgorithm {
  constructor(adam, config) {
    this.config = config || {
      populationSize: 10,
      mutationRate: 10,
      rotations: 4,
    };

    // population is an array of individuals. Each individual is a object representing the order of insertion and the angle each part is rotated
    var angles = [];
    for (var i = 0; i < adam.length; i++) {
      var angle =
        Math.floor(aleatorio() * this.config.rotations) *
        (360 / this.config.rotations);
      angles.push(angle);
    }

    this.population = [{ placement: adam, rotation: angles }];

    while (this.population.length < config.populationSize) {
      var mutant = this.mutate(this.population[0]);
      this.population.push(mutant);
    }
  }

  // returns a mutated individual with the given mutation rate
  mutate(individual) {
    var clone = {
      placement: individual.placement.slice(0),
      rotation: individual.rotation.slice(0),
    };
    for (var i = 0; i < clone.placement.length; i++) {
      var rand = aleatorio();
      if (rand < 0.01 * this.config.mutationRate) {
        // swap current part with next part
        var j = i + 1;

        if (j < clone.placement.length) {
          var temp = clone.placement[i];
          clone.placement[i] = clone.placement[j];
          clone.placement[j] = temp;
        }
      }

      rand = aleatorio();
      if (rand < 0.01 * this.config.mutationRate) {
        clone.rotation[i] =
          Math.floor(aleatorio() * this.config.rotations) *
          (360 / this.config.rotations);
      }
    }

    return clone;
  };

  // single point crossover
  mate(male, female) {
    var cutpoint = Math.round(
      Math.min(Math.max(aleatorio(), 0.1), 0.9) * (male.placement.length - 1)
    );

    var gene1 = male.placement.slice(0, cutpoint);
    var rot1 = male.rotation.slice(0, cutpoint);

    var gene2 = female.placement.slice(0, cutpoint);
    var rot2 = female.rotation.slice(0, cutpoint);

    for (var i = 0; i < female.placement.length; i++) {
      if (!contains(gene1, female.placement[i].id)) {
        gene1.push(female.placement[i]);
        rot1.push(female.rotation[i]);
      }
    }

    for (var i = 0; i < male.placement.length; i++) {
      if (!contains(gene2, male.placement[i].id)) {
        gene2.push(male.placement[i]);
        rot2.push(male.rotation[i]);
      }
    }

    function contains(gene, id) {
      for (var i = 0; i < gene.length; i++) {
        if (gene[i].id == id) {
          return true;
        }
      }
      return false;
    }

    return [
      { placement: gene1, rotation: rot1 },
      { placement: gene2, rotation: rot2 },
    ];
  };

  generation() {
    // Individuals with higher fitness are more likely to be selected for mating
    this.population.sort(function (a, b) {
      return a.fitness - b.fitness;
    });

    // fittest individual is preserved in the new generation (elitism)
    var newpopulation = [this.population[0]];

    while (newpopulation.length < this.population.length) {
      var male = this.randomWeightedIndividual();
      var female = this.randomWeightedIndividual(male);

      // each mating produces two children
      var children = this.mate(male, female);

      // slightly mutate children
      newpopulation.push(this.mutate(children[0]));

      if (newpopulation.length < this.population.length) {
        newpopulation.push(this.mutate(children[1]));
      }
    }

    this.population = newpopulation;
  };

  // returns a random individual from the population, weighted to the front of the list (lower fitness value is more likely to be selected)
  randomWeightedIndividual(exclude) {
    var pop = this.population.slice(0);

    if (exclude && pop.indexOf(exclude) >= 0) {
      pop.splice(pop.indexOf(exclude), 1);
    }

    var rand = aleatorio();

    var lower = 0;
    var weight = 1 / pop.length;
    var upper = weight;

    for (var i = 0; i < pop.length; i++) {
      // if the random number falls between lower and upper bounds, select this individual
      if (rand > lower && rand < upper) {
        return pop[i];
      }
      lower = upper;
      upper += 2 * weight * ((pop.length - i) / pop.length);
    }

    return pop[0];
  };
}


  return GeneticAlgorithm;
};
