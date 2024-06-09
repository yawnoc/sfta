import logging

import streamlit as st

from sfta.context_manager import DeepRecurse
from sfta.data_models.exceptions.base import FaultTreeTextException
from sfta.data_models.fault_tree import FaultTree
from sfta.output_handling import create_directory_robust, write_output_files

logging.basicConfig(level=logging.DEBUG)


def analyze_fault_tree(fault_tree_text):
    try:
        with DeepRecurse(recursion_limit=10**4):
            fault_tree = FaultTree(fault_tree_text)
    except FaultTreeTextException as exception:
        line_number = exception.line_number
        message = exception.message
        error_location_str = f'at line {line_number} ' if line_number else ''
        raise ValueError(f'Error {error_location_str}in fault tree text:\n  {message}')

    output_directory_name = 'output'
    create_directory_robust(output_directory_name)
    svg_file_paths = write_output_files(fault_tree, output_directory_name)

    return svg_file_paths


def main():
    st.set_page_config(page_title='Fault Tree Analysis Tool', layout='wide')

    st.title('Fault Tree Analysis Tool')
    st.write('Enter your fault tree text below and click "Generate Flowchart" to visualize the fault tree.')

    fault_tree_text = st.text_area('Fault Tree Text', height=300)

    col1, col2 = st.columns([1, 3])

    with col1:
        if st.button('Generate Flowchart'):
            if fault_tree_text:
                try:
                    svg_file_paths = analyze_fault_tree(fault_tree_text)
                    st.session_state.svg_file_paths = svg_file_paths
                    st.success('Flowchart generated successfully! Select an SVG file to display.')
                except ValueError as e:
                    st.error(str(e))
                except FileNotFoundError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f'An unexpected error occurred: {str(e)}')
            else:
                st.error('Please enter the fault tree text.')

        if 'svg_file_paths' in st.session_state:
            svg_file_paths = st.session_state.svg_file_paths
            selected_svg = st.selectbox('Select an SVG file to display:', svg_file_paths, key='svg_selector')

    with col2:
        if 'svg_file_paths' in st.session_state and st.session_state.svg_file_paths:
            if selected_svg:
                with open(selected_svg, 'r') as file:
                    svg_content = file.read()
                st.markdown(svg_content, unsafe_allow_html=True)
            else:
                st.info('Please generate and select an SVG file to display.')


if __name__ == '__main__':
    main()
