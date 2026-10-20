# References

## Similar projects

- [osaukh/pollenpub](https://github.com/osaukh/pollenpub): affordable automatic pollen
  monitor from ETH Zurich and TU Graz. Six inlets and a cyclone, a glycerine-coated glass
  plate, a microscope camera and YOLOv3 recognition. Material cost about €1000.
  Hardware, code and data are open (MIT). Paper: "Automated and Continuous Pollen Detection
  with an Affordable Technology" (EWSN 2020).
  [TU Graz article](https://tugraz.at/en/tu-graz/services/news-stories/tu-graz-news/singleview/article/pollenmesssystem-der-tu-graz-analysiert-pollen-schnell-guenstig-und-automatisch0).
- Ozcan lab (UCLA), "c-Air": a phone-based lensless camera for airborne particles,
  with deep learning. Wu et al., 2018. The closest research to our lensless approach.
- [Sensor.Community](https://sensor.community): citizen network of cheap fine dust sensors.
  A model for how a network like ours could work.

## How pollen is measured today

- [Hirst trap explained](https://uco.es/aerobiologia/metodologia/captacion_e.html)
  (University of Córdoba). The standard trap: a pump pulls 10 L/min through a 14 x 2 mm
  slot onto sticky tape on a slowly turning drum.
- [Hirst, 1952: An automatic volumetric spore trap](https://repository.rothamsted.ac.uk/id/eprint/20639).
  The original paper.
- [Jetschni & Jochner-Oette, 2021: Pollen sampler comparison](https://www.mdpi.com/2073-4433/12/8/974).
  Compares passive traps (pollen just lands on a surface) with traps that pull a known
  amount of air. Passive traps depend a lot on the wind, so you can't get grains per m³ from them.
- Astma-Allergi Danmark runs the Danish pollen counts (traps in Copenhagen and Viborg).

## Pollen image datasets

- [pollenpub dataset on Zenodo](https://zenodo.org/records/3572653)
- [Pollen13K](https://iplab.dmi.unict.it/pollengraindataset/): about 13,000 microscope pictures of pollen grains.
- [POLEN23E](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6138340/): 23 pollen types.

These are taken through real microscopes and look much sharper than our lensless pictures.
They're useful for pre-training and for learning what each pollen type looks like.
