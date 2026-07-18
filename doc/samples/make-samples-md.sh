#!/bin/bash

# Generate markdown doco for the lava DynamoDB item samples that is suitable
# for use in the lava user guide.

PROG=$(basename "$0")

SECTION_HEADER='##'

# With mkdocs material use an accordian instead of a heading to hold each sample

# SAMPLE_HEADER='####'
# SAMPLE_INDENT=''

SAMPLE_HEADER='???'
SAMPLE_INDENT='    '

# ------------------------------------------------------------------------------
function usage {
	cat <<!
	
Usage: $PROG template-dir

The specified template directory must contain built versions of the samples.
Sub-directories must indicate categories and contain the sample YAML files.

!
}

function title {
	python3 -c "print('$1'.replace('-', ' ').title())"
}

function stem {
	basename "${1%.*}"
}

# ------------------------------------------------------------------------------
[ $# -ne 1 ] && usage && exit 1

template_dir="$1"
[ ! -d "$template_dir" ] && echo "$PROG: $template_dir: No such directory" && exit 1

# ------------------------------------------------------------------------------
tmpdir=$(mktemp -d)
z=3
trap '/bin/rm -rf $tmpdir; exit $z' 0

# ------------------------------------------------------------------------------
find "$template_dir" -mindepth 1 -maxdepth 1 -type d | sort | while read -r dir
do
	category=$(basename "$dir")
	category_title=$(title "$category")
	echo "*   [$category_title samples](#$category-samples)" >> "$tmpdir/idx"
	echo "$SECTION_HEADER $category_title Samples" >> "$tmpdir/body"
	echo
	for sample_file in "$template_dir"/"$category"/[a-z]*.yaml
	do
		sample_name="$(stem "$sample_file")"

		echo "${SAMPLE_HEADER} \"$sample_name\""
		echo
		(
			echo '```yaml'
			cat "$sample_file"
			echo '```'
		) | sed "s/^/$SAMPLE_INDENT/"
		echo
	done >> "$tmpdir/body"
done

echo >> "$tmpdir/idx"

cat "$tmpdir/idx" "$tmpdir/body"
z=0
