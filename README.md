# Alcohol in traffic accidents and breathalyser tests in Slovenia

**Source of data**: Slovenian police (obtained by Access to Public Information Act), and [IK Data Hub](https://ikdatahub.si).

In December 2024 I received a file [PrometUkrepi_PolicijskeEnote_2005_2024_na_dan_20241206.xlsx](PrometUkrepi_PolicijskeEnote_2005_2024_na_dan_20241206.xlsx), containing police measures (breathalyzer, ethylometer, professional examination) related to the alcoholism of road users for the period from 1. 1. 2005 to 31. 10. 2024, by police administrative unit and area of ​​work.

**Please note** that those are **all breathalyser tests** - tests done by police when there is a traffic accident (in Slovenia police routinely breathalyse all active participants of traffic accident) **and** random tests carried out as part of traffic control.

File [Alcohol_tests_2005_2024.csv](Alcohol_tests_2005_2024.csv) contains preprocessed data:
- export of Excel tab of a data by police administrative unit and administrative unit ("PP in UE" tab);
- data are translated into English.

[IK Data Hub](https://ikdatahub.si) contains data about traffic accidents. I dowloaded absolute numbers of traffic accidents by administrative units and saved them into a file [Traffic_accidents_by_Administrative_Unit.csv](Traffic_accidents_by_Administrative_Unit.csv):
- all traffic accidents;
- traffic accidents without alcohol (filter "Breathalyser test value");
- traffic accidents with any alcohol (filter "Breathalyser test value");
- traffic accidents with allowed alcohol (filter "Breathalyser test value": 0.01 - 0.24 g/kg);
- traffic accidents with exceeded alcohol (filter "Breathalyser test value": more than 0.24 g/kg);

## Database

`sudo -u postgres psql`

Assuming user is `matej`: 

```
CREATE DATABASE alcohol OWNER matej;
GRANT ALL PRIVILEGES ON DATABASE alcohol TO matej;
```

`ctrl-d`

`psql -U matej -d alcohol

## Data about administrative units and police administrative units

```
CREATE TABLE units (unitid text, administrative_unit text, police_administrative_unit text);

\COPY units FROM 'List_of_AU_and_PAU.csv' WITH CSV header delimiter E'\t' quote '"';
```

## Breathalyser tests data

```
CREATE TABLE tests (year text, police_administration text, police_station text, muncipality text, administrative_unit text, area text, measure text, num_ordered_tests decimal(16), num_positive_tests decimal(16));

\COPY tests from 'Alcohol_tests_2005_2024.csv' with csv header delimiter E'\t' quote '"';
```

Create new variable `police_administrative_unit`.

IF:
field `police_administration` contains:
- `Uniformed Police Administration`
- `Center for Security and Protection`
- `SWAT`
- `Specialized Department of the Supreme State Prosecutor's Office`
- `Highway Police Administration`

THEN:
lookup `administrative_unit` in the table `units` and attribute the information about "Police administrative unit" from that table.

ELSE:
take "Police administrative unit".

```
ALTER TABLE tests ADD COLUMN police_administrative_unit text;

UPDATE tests SET police_administrative_unit = police_administration WHERE police_administration NOT IN ('Uniformed Police Administration', 'Center for Security and Protection', 'SWAT', 'Specialized Department of the Supreme State Prosecutor''s Office', 'Highway Police Administration');

UPDATE tests SET police_administrative_unit = units.police_administrative_unit FROM units WHERE (tests.police_administration IN ('Uniformed Police Administration', 'Center for Security and Protection', 'SWAT', 'Specialized Department of the Supreme State Prosecutor''s Office', 'Highway Police Administration')) AND (tests.administrative_unit=units.administrative_unit);
```

### View breathalyser data grouped by Police administrative unit

```
SELECT police_administrative_unit, sum(num_ordered_tests) AS num_ordered_brethalyser_tests, sum(num_positive_tests) AS num_positive_brethalyser_tests FROM tests WHERE year NOT IN ('2023', '2024') GROUP BY police_administrative_unit ORDER BY police_administrative_unit;
```

## Traffic accidents data

Source of data: `https://ikdatahub.si/en/dashboard/traffic-accidents` (`All cases` with appropriate filters; CSV files were then merged to a file `Traffic_accidents_by_Administrative_Unit.csv`).

```
CREATE TABLE accidents (unitid text, all_accidents decimal(16), without_alcohol decimal(16), with_alcohol decimal(16), with_allowed_alcohol decimal(16), with_exceeded_alcohol decimal(16));

\COPY accidents from 'Traffic_accidents_by_Administrative_Unit.csv' with csv header delimiter E'\t' quote '"';
```

### View accidents data grouped by Police administrative unit

```
SELECT units.police_administrative_unit, sum(accidents.all_accidents) AS all_accidents, sum(accidents.without_alcohol) AS accidents_without_alcohol, sum(accidents.with_alcohol) AS accidents_with_any_alcohol, sum(accidents.with_allowed_alcohol) AS accidents_with_allowed_alcohol, sum(accidents.with_exceeded_alcohol) AS accidents_exceeded_alcohol FROM accidents, units WHERE (units.unitid = accidents.unitid) GROUP BY units.police_administrative_unit ORDER BY 1;
```

## Create one table for accidents and breathalyser tests grouped by Police administrative unit

(*Since data from accidents are till end of 2022, we exclude data for 2023 and 2024 from breathalyser tests dataset.*)

```
CREATE TABLE accidents_and_breathalysers  (
    police_administrative_unit TEXT PRIMARY KEY,
    num_ordered_breathalyser_tests INT,
    num_positive_breathalyser_tests INT,
    all_accidents INT,
    accidents_without_alcohol INT,
    accidents_with_any_alcohol INT,
    accidents_with_allowed_alcohol INT,
    accidents_exceeded_alcohol INT
);


INSERT INTO accidents_and_breathalysers (
    police_administrative_unit,
    num_ordered_breathalyser_tests,
    num_positive_breathalyser_tests,
    all_accidents,
    accidents_without_alcohol,
    accidents_with_any_alcohol,
    accidents_with_allowed_alcohol,
    accidents_exceeded_alcohol
)
SELECT
    COALESCE(t.police_administrative_unit, a.police_administrative_unit) AS police_administrative_unit,
    COALESCE(t.num_ordered_breathalyser_tests, 0) AS num_ordered_breathalyser_tests,
    COALESCE(t.num_positive_breathalyser_tests, 0) AS num_positive_breathalyser_tests,
    COALESCE(a.all_accidents, 0) AS all_accidents,
    COALESCE(a.accidents_without_alcohol, 0) AS accidents_without_alcohol,
    COALESCE(a.accidents_with_any_alcohol, 0) AS accidents_with_any_alcohol,
    COALESCE(a.accidents_with_allowed_alcohol, 0) AS accidents_with_allowed_alcohol,
    COALESCE(a.accidents_exceeded_alcohol, 0) AS accidents_exceeded_alcohol
FROM (
    SELECT
        police_administrative_unit,
        SUM(num_ordered_tests) AS num_ordered_breathalyser_tests,
        SUM(num_positive_tests) AS num_positive_breathalyser_tests
    FROM tests
    WHERE year NOT IN ('2023', '2024')
    GROUP BY police_administrative_unit
) t
FULL OUTER JOIN (
    SELECT
        units.police_administrative_unit,
        SUM(accidents.all_accidents) AS all_accidents,
        SUM(accidents.without_alcohol) AS accidents_without_alcohol,
        SUM(accidents.with_alcohol) AS accidents_with_any_alcohol,
        SUM(accidents.with_allowed_alcohol) AS accidents_with_allowed_alcohol,
        SUM(accidents.with_exceeded_alcohol) AS accidents_exceeded_alcohol
    FROM accidents
    JOIN units ON units.unitid = accidents.unitid
    GROUP BY units.police_administrative_unit
) a
ON t.police_administrative_unit = a.police_administrative_unit
WHERE COALESCE(t.police_administrative_unit, a.police_administrative_unit) IS NOT NULL;
```

## Exporting data for drawing maps
The available SVG file contains only (smaller) administrative units, not police administrative units. Since police administrative units consist of multiple smaller administrative units, we need to group them so that all units within the same police administrative unit share the same value. This is done by assigning identical value to grouped units in the SVG file. Data with that values are then exported to CSV files.

### all_accidents
```
\COPY (SELECT unitid, all_accidents FROM accidents_and_breathalysers, units WHERE (accidents_and_breathalysers.police_administrative_unit = units.police_administrative_unit) ORDER BY 1) TO 'all_accidents.csv' WITH (FORMAT csv, HEADER true);
```

### accidents_without_alcohol
```
\COPY (SELECT unitid, accidents_without_alcohol FROM accidents_and_breathalysers, units WHERE (accidents_and_breathalysers.police_administrative_unit = units.police_administrative_unit) ORDER BY 1) TO 'accidents_without_alcohol.csv' WITH (FORMAT csv, HEADER true);
```

### accidents_with_any_alcohol
```
\COPY (SELECT unitid, accidents_with_any_alcohol FROM accidents_and_breathalysers, units WHERE (accidents_and_breathalysers.police_administrative_unit = units.police_administrative_unit) ORDER BY 1) TO 'accidents_with_any_alcohol.csv' WITH (FORMAT csv, HEADER true);
```

### accidents_with_allowed_alcohol
```
\COPY (SELECT unitid, accidents_with_allowed_alcohol FROM accidents_and_breathalysers, units WHERE (accidents_and_breathalysers.police_administrative_unit = units.police_administrative_unit) ORDER BY 1) TO 'accidents_with_allowed_alcohol.csv' WITH (FORMAT csv, HEADER true);
```

### accidents_exceeded_alcohol
```
\COPY (SELECT unitid, accidents_exceeded_alcohol FROM accidents_and_breathalysers, units WHERE (accidents_and_breathalysers.police_administrative_unit = units.police_administrative_unit) ORDER BY 1) TO 'accidents_exceeded_alcohol.csv' WITH (FORMAT csv, HEADER true);
```

### num_ordered_brethalyser_tests
```
\COPY (SELECT unitid, num_ordered_breathalyser_tests FROM accidents_and_breathalysers, units WHERE (accidents_and_breathalysers.police_administrative_unit = units.police_administrative_unit) ORDER BY 1) TO 'num_ordered_brethalyser_tests.csv' WITH (FORMAT csv, HEADER true);
```

### num_positive_brethalyser_tests
```
\COPY (SELECT unitid, num_positive_breathalyser_tests FROM accidents_and_breathalysers, units WHERE (accidents_and_breathalysers.police_administrative_unit = units.police_administrative_unit) ORDER BY 1) TO 'num_positive_brethalyser_tests.csv' WITH (FORMAT csv, HEADER true);
```

### ordered_breathalysers_per_all_accidents
(num_ordered_breathalyser_tests / all_accidents * 100)

```
\COPY (SELECT unitid, (num_ordered_breathalyser_tests::DECIMAL / all_accidents::DECIMAL * 100) AS ordered_breathalysers_per_all_accidents FROM accidents_and_breathalysers, units WHERE (accidents_and_breathalysers.police_administrative_unit = units.police_administrative_unit) ORDER BY 1) TO 'ordered_breathalysers_per_all_accidents.csv' WITH (FORMAT csv, HEADER true);
```

### accidents_with_any_alcohol_per_ordered_breathalysers
(accidents_with_any_alcohol / num_ordered_breathalyser_tests * 100)

```
\COPY (SELECT unitid, (accidents_with_any_alcohol::DECIMAL / num_ordered_breathalyser_tests::DECIMAL * 100) AS accidents_with_any_alcohol_per_ordered_breathalysers FROM accidents_and_breathalysers, units WHERE (accidents_and_breathalysers.police_administrative_unit = units.police_administrative_unit) ORDER BY 1) TO 'accidents_with_any_alcohol_per_ordered_breathalysers.csv' WITH (FORMAT csv, HEADER true);
```

### accidents_with_exceeded_alcohol_per_ordered_breathalysers
(accidents_exceeded_alcohol / num_ordered_breathalyser_tests * 100)
```
\COPY (SELECT unitid, (accidents_exceeded_alcohol::DECIMAL / num_ordered_breathalyser_tests::DECIMAL * 100) AS accidents_with_exceeded_alcohol_per_ordered_breathalysers FROM accidents_and_breathalysers, units WHERE (accidents_and_breathalysers.police_administrative_unit = units.police_administrative_unit) ORDER BY 1) TO 'accidents_with_exceeded_alcohol_per_ordered_breathalysers.csv' WITH (FORMAT csv, HEADER true);
```

### positive_breathalysers_per_ordered_breathalysers
(num_positive_breathalyser_tests / num_ordered_breathalyser_tests * 10)
```
\COPY (SELECT unitid, (num_positive_breathalyser_tests::DECIMAL / num_ordered_breathalyser_tests::DECIMAL * 10) AS positive_breathalysers_per_ordered_breathalysers FROM accidents_and_breathalysers, units WHERE (accidents_and_breathalysers.police_administrative_unit = units.police_administrative_unit) ORDER BY 1) TO 'positive_breathalysers_per_ordered_breathalysers.csv' WITH (FORMAT csv, HEADER true);
```

## Drawing maps

For drawing maps we use Python files [colorize.py](colorize.py) and [colorize-ratios.py](colorize-ratios.py). File `colorize.py` draws a map with blue shades and a legend and file `colorize-ratios.py` draws a map with green shades and without a legend. Parameters are:
- input file with data in CSV format
- title of the map

### Draw basic maps
*Blue map with legend.*

```
python3 colorize.py all_accidents.csv "Number of all traffic accidents"
python3 colorize.py accidents_without_alcohol.csv "Number of traffic accidents without alcohol"
python3 colorize.py accidents_with_allowed_alcohol.csv "Number of traffic accidents with allowed alcohol value"
python3 colorize.py accidents_exceeded_alcohol.csv "Number of traffic accidents with exceeded alcohol value"
python3 colorize.py accidents_with_any_alcohol.csv "Number of traffic accidents with any alcohol value"
python3 colorize.py num_ordered_brethalyser_tests.csv "Number of ordered breathalyser tests"
python3 colorize.py num_positive_brethalyser_tests.csv "Number of positive breathalyser tests"
```

![slika](https://github.com/user-attachments/assets/b6e34173-4bfb-4db5-a378-47d19c3cf750)

### Draw ratio maps
*Green map without legend.*

```
python3 colorize-ratios.py ordered_breathalysers_per_all_accidents.csv "Ordered breathalyser tests per all accidents"
python3 colorize-ratios.py accidents_with_any_alcohol_per_ordered_breathalysers.csv "Accidents with  any alcohol value per ordered breathalysers"
python3 colorize-ratios.py accidents_with_exceeded_alcohol_per_ordered_breathalysers.csv "Accidents with exceeded alcohol value per ordered breathalysers"
python3 colorize-ratios.py positive_breathalysers_per_ordered_breathalysers.csv "Positive breathalysers per ordered breathalysers"
```

![slika](https://github.com/user-attachments/assets/c8908567-884b-41c1-8677-6bba55800a88)

![ratios](https://github.com/user-attachments/assets/c269ac55-cfb5-4ae2-a278-29311c2ea097)

## Interpretation

Ratio of how many breathalyzer tests were ordered per all accidents (ordered breathalyzers per 100 accidents) shows that there are differences among police administrative units. Some police units conduct more breathalyzer tests per accident than others.

It seems that **PU Nova Gorica** has the highest alcohol-related accident ratio, however they conduct relatively less breathalyzer tests than others. **PU Novo mesto** and **PU Murska Sobota** on the other hand have the highest testing rates.

This could indicate differences in enforcement policies. Data show a possible under-testing issue in **PU Nova Gorica** (more testing could be needed to identify alcohol-impaired drivers). On the other hand, in **Novo mesto** and **Murska Sobota**, police are ordering more breathalyzer tests per accident, which indicate a stricter enforcement policy, but it could also mean a higher **suspicion** of alcohol involvement in driving.

The ratio of how many accidents involved alcohol out of all the breathalyzer tests conducted (Accidents with any alcohol / Ordered breathalyzers) suggests higher correlation between accidents and alcohol consumption in **PU Nova Gorica** and **PU Koper**.

The data show the need for comparing enforcement policies with police units like **PU Novo mesto** (which has a high testing rate) and **PU Nova Gorica** (and also **PU Koper**). There could be some local factors (Nova Gorica nad Koper are border regions, there could be different cultural drinking habits or they might have more night clubs) or differences in enforcement policies **or resources**, that might explain why Nova Gorica has such a high alcohol-accident correlation and under-testing.
