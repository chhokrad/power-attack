input_filename=$(realpath $1)
output_filename=$(basename -- "$input_filename")
output_filename="${output_filename%.*}.dot"
echo "$output_filename"

if [ -f $output_filename ] ; then 
    rm -f $output_filename
fi

textx check $input_filename
textx generate $input_filename --target dot
