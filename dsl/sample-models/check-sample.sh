sample_model_filename=$(realpath $2)
meta_model_filename=$(realpath $1)
output_filename=$(basename -- "$sample_model_filename")
output_filename="${output_filename%.*}.dot"
echo "$output_filename"

if [ -f $output_filename ] ; then 
    rm -f $output_filename
fi

textx check $sample_model_filename --grammar $meta_model_filename 
textx generate $sample_model_filename --grammar $meta_model_filename --target dot
