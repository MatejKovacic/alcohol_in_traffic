# Alcohol in traffic accidents and breathalyser tests in Slovenia

**Source of data**: Slovenian police (obtained by Access to Public Information Act), and [IK Data Hub](https://ikdatahub.si).

In December 2024 I received a file [PrometUkrepi_PolicijskeEnote_2005_2024_na_dan_20241206.xlsx], containing police measures (breathalyzer, ethylometer, professional examination) related to the alcoholism of road users for the period from 1. 1. 2005 to 31. 10. 2024, by police administrative unit and area of ​​work. File [Alcohol_tests_2005_2024.csv] contains preprocessed data:
- export of Excel tab of a data by police administrative unit and administrative unit ("PP in UE" tab);
- data are translated into English.

[IK Data Hub](https://ikdatahub.si) contains data about traffic accidents. I dowloaded absolute numbers of traffic accidents by administrative units and saved them into a file [Traffic_accidents_by_Administrative_Unit.csv]:
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

## Drawing maps

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
(accidents_with_any_alcohol / num_ordered_breathalyser_tests * 1000)

```
\COPY (SELECT unitid, (accidents_with_any_alcohol::DECIMAL / num_ordered_breathalyser_tests::DECIMAL * 100) AS accidents_with_any_alcohol_per_ordered_breathalysers FROM accidents_and_breathalysers, units WHERE (accidents_and_breathalysers.police_administrative_unit = units.police_administrative_unit) ORDER BY 1) TO 'accidents_with_any_alcohol_per_ordered_breathalysers.csv' WITH (FORMAT csv, HEADER true);
```

### accidents_with_exceeded_alcohol_per_ordered_breathalysers
(accidents_exceeded_alcohol / num_ordered_breathalyser_tests * 1000)
```
\COPY (SELECT unitid, (accidents_exceeded_alcohol::DECIMAL / num_ordered_breathalyser_tests::DECIMAL * 100) AS accidents_with_exceeded_alcohol_per_ordered_breathalysers FROM accidents_and_breathalysers, units WHERE (accidents_and_breathalysers.police_administrative_unit = units.police_administrative_unit) ORDER BY 1) TO 'accidents_with_exceeded_alcohol_per_ordered_breathalysers.csv' WITH (FORMAT csv, HEADER true);
```

### positive_breathalysers_per_ordered_breathalysers
(num_positive_breathalyser_tests / num_ordered_breathalyser_tests * 1000)
```
\COPY (SELECT unitid, (num_positive_breathalyser_tests::DECIMAL / num_ordered_breathalyser_tests::DECIMAL * 10) AS positive_breathalysers_per_ordered_breathalysers FROM accidents_and_breathalysers, units WHERE (accidents_and_breathalysers.police_administrative_unit = units.police_administrative_unit) ORDER BY 1) TO 'positive_breathalysers_per_ordered_breathalysers.csv' WITH (FORMAT csv, HEADER true);
```

### Draw basic maps
Blue map with legend.

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
Green map without legend.

```
python3 colorize-ratios.py ordered_breathalysers_per_all_accidents.csv "Ordered breathalyser tests per all accidents"
python3 colorize-ratios.py accidents_with_any_alcohol_per_ordered_breathalysers.csv "Accidents with  any alcohol value per ordered breathalysers"
python3 colorize-ratios.py accidents_with_exceeded_alcohol_per_ordered_breathalysers.csv "Accidents with exceeded alcohol value per ordered breathalysers"
python3 colorize-ratios.py positive_breathalysers_per_ordered_breathalysers.csv "Positive breathalysers per ordered breathalysers"
```

![slika](https://github.com/user-attachments/assets/c8908567-884b-41c1-8677-6bba55800a88)

![ratios](https://github.com/user-attachments/assets/c269ac55-cfb5-4ae2-a278-29311c2ea097)
