#!/usr/bin/env python3

import argparse
from datetime import date, timedelta
from dateutil.parser import parse
import json
from math import floor
import os
import requests
import sys

######################## FRENCH LOCAL AREA ########################

# local_area = "alsace-moselle"
# local_area = "guadeloupe"
# local_area = "guyane"
# local_area = "la-reunion"
# local_area = "martinique"
# local_area = "mayotte"
local_area = "metropole"
# local_area = "nouvelle-caledonie"
# local_area = "polynesie-francaise"
# local_area = "saint-barthelemy"
# local_area = "saint-martin"
# local_area = "saint-pierre-et-miquelon"
# local_area = "wallis-et-futuna"


# Local area is needed for public holidays dates
def get_local_public_holidays(local_area, year):
    """Store it into a file local public holidays for a year in an area
    if it doesn't already exist (request on api.gouv.fr)"""
    filename = f"{local_area}_{year}.json"

    if not os.path.exists(filename):
        if args.verbose:
            print(f"\033[;2mLoading public holidays for {local_area}_{year}...\033[0m")

        link = (
            f"https://calendrier.api.gouv.fr/jours-feries/{filename.replace('_','/')}"
        )
        try:
            res = requests.get(link, allow_redirects=True)
            if not res.status_code == 200:
                raise Exception(res.status_code)
            fw = open(filename, "wb")
            fw.write(res.content)
            fw.close()
        except Exception as e:
            print(
                f"\033[33mAttention :\033[0m les jours fériés pour l'année {year} ne peuvent pas être téléchargés."
            )


######################## END FOR FRENCH LOCAL AREA ########################


def get_date(dt):
    try:
        return parse(dt, dayfirst=True)
    except ValueError:
        print(f"\033[31mError : \033[0m{dt} ne peut pas être interprété comme une date")
        return False


# Parser initialization
parser = argparse.ArgumentParser(
    description="Outil de calcul du nombre d'heures de travail et de la gratification résultante."
)
parser.add_argument(
    "date_debut", type=lambda s: get_date(s), help="date de début de stage (JJ/MM/AAAA)"
)
parser.add_argument(
    "date_fin", type=lambda s: get_date(s), help="date de fin de stage (JJ/MM/AAAA)"
)

parser.add_argument(
    "-v", "--verbose", action="store_true", help="increase output verbosity"
)
parser.add_argument(
    "-hours",
    type=float,
    default=7,
    metavar="X",
    help="nombre d'heures de stage par jour (%(default)sh/j par défaut)",
)
parser.add_argument(
    "-grat",
    type=float,
    default=4.05,
    metavar="X.X",
    help="gratification horaire du stage (%(default)s€/h par défaut)",
)
parser.add_argument(
    "-bonus",
    type=float,
    default=0.0,
    metavar="X.X",
    help="prime de fin de stage (%(default)s%% de la gratification totale par défaut)",
)
parser.add_argument(
    "-add",
    nargs="+",
    choices={"saturday", "sunday"},
    metavar="weekday",
    help="ajouter des jours exceptionnels de travail (saturday, sunday)",
)
parser.add_argument(
    "-rm",
    nargs="+",
    choices={"monday", "tuesday", "wednesday", "thursday", "friday"},
    metavar="weekday",
    help="retirer des jours de travail en semaine (monday, tuesday, ...)",
)
parser.add_argument(
    "-exclude",
    nargs="+",
    metavar="dday day_from-day_to",
    default=[],
    help="retirer des dates (fermetures, ponts ...)",
)

# Input checking
args = parser.parse_args()

date_begin, date_end = (
    (args.date_debut, args.date_fin)
    if args.date_debut < args.date_fin
    else (args.date_fin, args.date_debut)
)

hours_per_day = args.hours
if hours_per_day <= 0:
    print(
        "\033[31mErreur :\033[0m le nombre d'heures de stage par jour doit être un entier positif"
    )
    sys.exit(1)

hourly_gratification = args.grat
if hourly_gratification < 0.0:
    print(
        "\033[31mErreur :\033[0m la gratification doit être indiquée comme un flottant positif"
    )
    sys.exit(1)

bonus = args.bonus
if bonus < 0.0 or bonus > 100.0:
    print(
        "\033[31mErreur :\033[0m le pourcentage de prime doit être indiquée comme un flottant entre 0 et 100"
    )
    sys.exit(1)
# Process as float between 0 and 1, not as percentage
bonus /= 100.0

# Working weekdays
all_days = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]
not_working_days = ["saturday", "sunday"]  # Default week-end
working_days_name = []

if args.add:
    for ex_day in args.add:
        not_working_days.remove(ex_day)
if args.rm:
    not_working_days.extend(args.rm)

working_days_name.extend([day for day in all_days if day not in not_working_days])


# Get local public holidays during years of the internship
start_int_year = date_begin.year
end_int_year = date_end.year
public_holidays_local = {}
while start_int_year <= end_int_year:
    filename = f"{local_area}_{start_int_year}.json"
    get_local_public_holidays(local_area, start_int_year)

    if os.path.exists(filename):
        fo = open(filename, "r")
        public_holidays_local.update(json.loads("".join(fo.readlines())))
        fo.close()

    start_int_year += 1


# Gratification calculation

working_days = 0
completed_days = 0
hours = 0
free_days_off = []
exclude_days = []
excluded_days = []

for dt in args.exclude:
    if "-" in dt:
        db = get_date(dt.split("-")[0])
        de = get_date(dt.split("-")[1])
        if db == False or de == False:
            continue
        range_days = [
            (date(db.year, db.month, db.day) + timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range((de - db).days + 1)
        ]
        exclude_days.extend(range_days)
    elif d := get_date(dt):
        exclude_days.append(d.strftime("%Y-%m-%d"))

for i in range((date_end - date_begin).days + 1):
    day = date(date_begin.year, date_begin.month, date_begin.day) + timedelta(days=i)
    day_name = day.strftime("%A")
    if day_name.lower() in not_working_days:
        continue

    day_strftime = day.strftime("%Y-%m-%d")

    if day_strftime in public_holidays_local:
        free_days_off.append(
            f"{public_holidays_local[day_strftime]} ({day_name} {day.strftime('%d/%m/%Y')})"
        )
        continue
    elif day_strftime in exclude_days:
        excluded_days.append(f"{day_name} {day.strftime('%d/%m/%Y')}")
        continue
    else:
        working_days += 1
        if day < date.today():
            completed_days += 1

hours = hours_per_day * working_days
working_hours_count = working_days * hours_per_day
completed_hours_count = completed_days * hours_per_day
gratification_count = working_days * hours_per_day * hourly_gratification
bonus_count = gratification_count * bonus
gratification_with_bonus = gratification_count + bonus_count

days_off = (
    0 if working_hours_count <= 44 * 7 else working_hours_count / (22 * 7) * 2.5
)  # congés

# Output

print(f"\n==== Du {date_begin.strftime('%m/%d/%Y')} au {date_end.strftime('%m/%d/%Y')}")
print(f"==== {hours_per_day} heures par jour | {hourly_gratification}€ par heure")
print(
    f"==== Jours de stage : {', '.join(working_days_name)} ({len(working_days_name)} jours sur 7)\n"
)

print(f"> Nombre total de jours de stage           : {working_days}")
print(f"> Nombre total d'heures de stage           : {working_hours_count}")
if len(free_days_off) > 0:
    print(f"> Jours fériés pendant votre stage         : {len(free_days_off)}")
    if args.verbose:
        print("\n".join([f"\t\033[;2m{day}\033[0m" for day in free_days_off]))
    else:
        print("\t\033[;2m(Relancez avec l'option -v pour voir le détail)\033[0m")

if len(excluded_days) > 0:
    print(f"> Jours exclus pendant votre stage         : {len(excluded_days)}")
    if args.verbose:
        print("\n".join([f"\t\033[;2m{day}\033[0m" for day in excluded_days]))
    else:
        print("\t\033[;2m(Relancez avec l'option -v pour voir le détail)\033[0m")


print(f"> Estimation gratification totale          : {gratification_with_bonus:.1f}€")
if args.verbose:
    print(f"\033[2m\tGratification du stage             : {gratification_count:.1f}€")
    print(f"\tPrime de fin de stage              : {bonus_count:.1f}€\033[0m")
else:
    print("\t\033[;2m(Relancez avec l'option -v pour voir le détail)\033[0m")
print(f"> Estimation du nombre de jours de congé   : {floor(days_off):.0f}\n")

print(
    f"> Progression jours de stage               : {completed_days/working_days*100:.1f}% ({completed_days}/{working_days} | {working_days-completed_days} restants)"
)
print(
    f"> Progression heures de stage              : {completed_hours_count/working_hours_count*100:.1f}% ({completed_hours_count}/{working_hours_count} | {working_hours_count-completed_hours_count} restantes)"
)
print(
    f"> Progression gratification du stage       : {hourly_gratification * completed_hours_count:.1f}€/{gratification_count:.1f}€"
)
print(
    "\n\033[1mDisclaimer:\033[0m La gratification et les jours de congés sont des estimations, et peuvent différer en fonction de l'employeur."
)
print(
    "\tPlus d'informations sur \033[2mhttps://www.service-public.fr/professionnels-entreprises/vosdroits/F32131\033[0m"
)
