from __future__ import absolute_import
import json
import re
from tools.UI.ProcessedResultDict import ResultKeys, SectionDomain
from collections import OrderedDict
from tools.global_enums import States
from tools.global_logging import log_and_print
from six.moves import range

class HTMLBuilder:
    def __init__(self, out_file_path, use_default_style=True):
        self.out_file_path = out_file_path
        self.body = ""
        self.style = ""
        self.script = ""
        self._set_script()
        if use_default_style:
            self.set_default_style()

    def _set_script(self):
        self.script = """
        <script>
        function hideShowElement(detailsElement){
            if (detailsElement.className=="details"){
                if (detailsElement.style.display=="none" |detailsElement.style.display==""  ) {
                    detailsElement.style.display="contents";

                }
                else{
                    detailsElement.style.display="none";
                }
            }
        }
        function hideShowElement_v2(nr) {
            table_list = document.querySelectorAll(`[id^="table"]`);
			tab_list = document.querySelectorAll(`[id^="tab"]`);
			for (let i = 0; i < table_list.length; i++) {
				table_list[i].style.display="none";
				tab_list[i].classList.remove("active");
			}
            document.getElementById("table"+nr).style.display="block";
            document.getElementById("tab"+nr).classList.add("active");
            }
        
        function changeText(e, longText, shortText, attributes_dict) {
            let elementId = e.target.id? e.target.id: e.target.closest("td").id;
            let element = document.getElementById(elementId)  
            var txt = document.createElement("textarea");
            txt.innerHTML = element.innerHTML;
            if (txt.value == longText) {
                element.innerHTML = shortText;
                element.style.textAlign = 'center';
            }
            else {
                element.innerHTML = longText;  
                if (attributes_dict){
                    for(key in attributes_dict){
                        element.style[key] = attributes_dict[key];
                    }
                }
            }               
        }

        function showMoreLess(e, allResults) {
            button = e.target;
            buttonRow = button.closest('tr');
            parent = e.target.parentElement;
            tbody = parent.closest('tbody');
            rowsArray = tbody.getElementsByTagName("tr");
            let remarks = null;
            if (rowsArray[rowsArray.length-1].getElementsByTagName("td")[0].colSpan > 1 && rowsArray[rowsArray.length-1].getElementsByTagName("td")[0].firstChild.nodeName=="#text"){
                remarks=rowsArray[rowsArray.length-1];
            }
            numTopHeaders = countHeaders(rowsArray)  
            numFooters = countHeaders(Array.from(rowsArray).reverse())
            if (button.textContent=='show more'){
                showMore(allResults,buttonRow,remarks,tbody,button, numTopHeaders, numFooters)
            }
            else {
                if (button.textContent=='show less'){
                    showLess(remarks, tbody, rowsArray, button, numTopHeaders, numFooters)
                }
            }
        }
        
        function countHeaders(rowsArray){
            numHeaders = 0;
            for (let i=0; i < rowsArray.length; i++){
                if (rowsArray[i].children[0].tagName == "TH" || (rowsArray[i].children[0].tagName == "TD" && rowsArray[i].getElementsByTagName("td")[0].getAttribute("colspan"))){
                    numHeaders++;
                }
                else{
                    break;
                }
            }
            return numHeaders
        }

        function showMore(allResults, buttonRow, remarks, tbody, button, numTopHeaders, numFooters){
            let lastResult = rowsArray.length - numTopHeaders - numFooters;
            let tr = null;
            for (let i = lastResult; i < allResults.length && i < allResults.length; i++){
                if (i == lastResult){
                    tbody.removeChild(buttonRow);
                    if (remarks){
                        tbody.removeChild(remarks);
                    }
                }
                tr = document.createElement("tr");
                for (let j = 0; j < allResults[i].length; j++){
                    td = document.createElement("td");
                    td.title="";
                    for(key in allResults[i][j]){
                        td.innerHTML=key;
                        td.style.cssText = allResults[i][j][key].style;
                    }
                    tr.appendChild(td);
                }
                tbody.appendChild(tr);
            }
            if (tr){
                tbody.appendChild(buttonRow);
                if (remarks){
                    tbody.appendChild(remarks);
                }
            } 
            button.textContent='show less';
        }

        function showLess(remarks, tbody, rowsArray, button, numTopHeaders, numFooters){
            if (remarks){
                tbody.appendChild(remarks);
            }                
            for (let i = rowsArray.length - 1 - numFooters; i >= 6 + numTopHeaders ; i--) {
                tbody.removeChild(rowsArray[i])
            }
            button.textContent='show more';
        }
      
        function openTab(elemntId, idPrefix) {
            var i, tabContent, tabLabels;
            
            // Get all elements with class="tabContent" and hide them
            tabContent = document.getElementsByClassName("tabContent");
            for (i = 0; i < tabContent.length; i++) {
                if (tabContent[i].id.includes(idPrefix)){
                    tabContent[i].style.display = "none";
                }               
            }
            
            // Get all elements with class="tab-label" and remove the class "active"
            tabLabels = document.getElementsByClassName("tab-label");
            for (i = 0; i < tabLabels.length; i++) {
                if (tabLabels[i].id.includes(idPrefix)){
                    tabLabels[i].className = tabLabels[i].className.replace(" active", "");
                }             
            }
            
            // Show the current tab, and add an "active" class to the button that opened the tab
            document.getElementById("innerTab" + elemntId).style.display = "block";
            document.getElementById(elemntId).className += " active";
        }   
        function navigate_to_information_validation_by_link(infoClassName, isInnerTab) {
            let infoElementsList = document.getElementsByClassName(infoClassName); 
        
            if (isInnerTab) {
                let tabId = infoElementsList[0].closest('[id^=innerTabvalidations]').id.replace("innerTab", "");
                openTab(tabId, "validations");
                window.scrollTo(0, 0);
            } else {
                let tableId = infoElementsList[0].closest('[id^=table]').id;
                hideShowElement_v2(tableId.slice(-1)[0]);  
        
                for (let i = 0; i < infoElementsList.length; i++) {
                    let infoElement = infoElementsList[i];
                    if (infoElement.tagName == "BUTTON") {
                        infoElement.click();
                    } else {
                        if (infoElement.closest('div.details')) {
                            infoElement.closest('div.details').style.display = "contents";
                            if (infoElement.closest('.details').style.display != "contents") {
                                infoElement.closest('.details').style.display = "contents";
                            }
                        }
                    }
                }
                let tabsTool = document.getElementsByClassName("summary_white_bg")[0];
                window.scrollTo(0, infoElementsList[0].offsetTop - tabsTool.offsetHeight - tabsTool.offsetTop);
            }
        }
        </script>
        """

    def set_default_style(self):
        self.add_style(
            'body', {
                "font-family": "system-ui, arial, sans-serif",
                "text-align": "center",
                "margin": "0",
                "padding": "0",
                "background": "#efebeb",
                "min-height": "100vh",
                "margin-bottom": "40px !important",
                "display": "flex",
                "flex-direction": "column"
            })
        self.add_style(
            '.tabContent', {
                'display': 'none'
            }
        )
        self.add_style(
            'table , .table_header', {
                "border": "1px solid black",
                "border-collapse": "collapse",
                "table-layout": "fixed",
                "width": "100%"
            })
        self.add_style(
            '.center', {
                "margin": "1% auto"
            })
        self.add_style(
            '.width_90', {
                "width": "90%",
            })
        self.add_style(
            '.width_80', {
                "width": "80%",
            })
        self.add_style(
            '.width_85', {
                "width": "85%",
            })
        self.add_style(
            '.padding', {
                "padding": "1%"
            })
        self.add_style(
            '.margin', {
                "margin": "1%"
            })
        self.add_style(
            'td, th', {
                "text-align": "center",
                "padding": "8px",
                "word-break": "break-word",
                "background": "white"
            })
        self.add_style(
            '.fixTableHead', {
                "overflow-y": "auto",
                "height": "77vh",
            })
        self.add_style(
            '.fixTableHead thead th', {
                "position": "sticky",
                "top": 0,
            })
        self.add_style(
            '.light_background', {
                "background-color": "#c8e4fd",
            })
        self.add_style(
            '.summary', {
                "cursor": "pointer"
            })
        self.add_style(
            '.details', {
                "display": "none",
                "padding-top": "100px"
            })
        self.add_style(
            '.dotted', {
                "border": "black 1.5px dotted"
            })
        self.add_style(
            '.background_2', {
                "background-color": "#679dbb",
                "color": "white"
            })
        self.add_style(
            '.background_3', {
                "background-color": "#5386a2",
                "color": "white"
            })
        self.add_style(
            '.background_4', {
                "background-color": "#793c5e",
                "color": "white"
            })
        self.add_style(
            '.background_5', {
                "background-color": "#1f5573",
                "color": "white"
            })
        self.add_style(
            '.middle_font', {
                "font-size": "large",
                "font-weight": "bold"
            })
        self.add_style(
            '.small_font', {
                "font-size": "small",
                "font-weight": "bold"
            })
        self.add_style(
            '.title', {
                "margin-left": "12px",
                "font-size": "15px",
                "color": "#fff",
                "opacity": ".75"
            })
        self.add_style(
            '.logo', {
                "margin-left": "24px",
                "margin-top": "2px"
            })
        self.add_style(
            '.version', {
                "margin-left": "auto",
                "margin-right": "24px",
                "color": "#fff",
                "font-size": "14px"
            })
        self.add_style(
            '.header-bar', {
                "background-color": "rgb(18, 65, 145)",
                "height": "50px",
                "z-index": "12000",
                "width": "100%",
                "display": "flex",
                "align-items": "center",
                "position": "relative"
            })
        self.add_style(
            '.summary_white_bg', {
                "background": "#fafafa",
                "display": "flex",
                "position": "fixed",
                "width": "100%",
                "top": "50px",
                "overflow": "auto"
            })
        self.add_style(
            '.top-bar', {
                "position": "fixed",
                "width": "100%",
                "top": "0"
            })
        self.add_style(
            '.tab-label:hover', {
                "color": "rgb(18 65 145 / 89%)",
            })
        self.add_style(
            '.active', {
                "color": "#124191 !important",
                "border-bottom": "4px solid #124191 !important"
            })
        self.add_style(
            '.tab-label', {
                "height": "48px",
                "flex": "none",
                "display": "inline-block",
                "overflow": "hidden",
                "position": "relative",
                "cursor": "pointer",
                "max-width": "264px",
                "min-width": "164px",
                "padding": "16px 24px",
                "margin": "0",
                "background": "transparent",
                "border": "0",
                "box-sizing": "border-box",
                "color": "rgb(0 0 0 / 87%)",
                "text-transform": "uppercase",
                "font-weight": "600"
            })
        self.add_style(
            'footer', {
                "position": "fixed",
                "left": "0",
                "bottom": "0",
                "width": "100%",
                "height": "40px",
                "background": "rgb(18, 65, 145)",
                "align-items": "center",
                "display": "flex",
                "color": "#fff",
                "font-size": "14px"
            })
        self.add_style(
            '.footer-left', {
                "margin-left": "30px"
            })
        self.add_style(
            '.footer-right', {
                "margin-left": "auto",
                "margin-right": "30px"
            })
        self.add_style(
            '.footer-center', {
                "margin-left": "auto",
                "margin-right": "auto",
                "text-align": "center",
                "width": "100%"
            })
        self.add_style(
            '#footer-link', {
                "color": "#fff",
                "text-decoration": "none"
            })
        self.add_style(
            '.show-more-less-button', {
                "width": "100%",
                "color": "white",
                "padding": "16px",
                "background-color": "gray",
                "border": "none",
                "cursor": "pointer",
                "text-transform": "uppercase"
            })

    @staticmethod
    def create_main_section_element(title, section_element, number, is_expandable=True, active=False):
        properties_dict = {}
        title_properties = {
            "class": "summary dotted padding width_90 center"
        }
        if is_expandable:
            properties_dict["class"] = "details"
            properties_dict["id"] = "table" + str(number)
            title_properties["onclick"] = "hideShowElement(event.target.nextElementSibling)"
        if active:
            properties_dict["style"] = "display: block"
        section_element = HTMLBuilder.create_element('div', [section_element], properties_dict)
        # title_element = HTMLBuilder.create_element('div', [title], title_properties)
        container_element = HTMLBuilder.create_element('div', [  # title_element,
            section_element])
        return container_element

    @staticmethod
    def create_title_bar(title):
        title_properties = {
            "class": "summary_white_bg"
        }

        section_collection = []
        for i in range(0, len(title)):
            if i == 0:
                properties_dict = {
                    "class": "tab-label active",
                }
            else:
                properties_dict = {
                    "class": "tab-label",
                }
            properties_dict["onclick"] = "hideShowElement_v2(" + str(i + 1) + ")"
            properties_dict["id"] = "tab" + str(i + 1)
            section_element = HTMLBuilder.create_element('button', [title[i]], properties_dict)
            section_collection.append(section_element)

        title_element = HTMLBuilder.create_element('div', section_collection, title_properties)
        return title_element

    @staticmethod
    def create_inner_tab_bar(title_list, id_prefix, classes_list):
        assert len(title_list) == len(classes_list), "Expected to have class_name for every tab"
        section_collection = []
        for i, title in enumerate(title_list):
            if i == 0:
                properties_dict = {
                    "class": "tab-label active {}".format(classes_list[i]),
                }
            else:
                properties_dict = {
                    "class": "tab-label {}".format(classes_list[i]),
                }
            properties_dict["id"] = id_prefix + title
            properties_dict["onclick"] = "openTab('{}', '{}')".format(properties_dict["id"], id_prefix)
            properties_dict["style"] = "white-space: nowrap;"
            section_element = HTMLBuilder.create_element('button', [title], properties_dict)
            section_collection.append(section_element)
        title_element = HTMLBuilder.create_element('div', section_collection)
        return title_element

    @staticmethod
    def create_sub_section_element(
            title, sub_section_element, is_width_smaller=False, is_expandable=True, background_color=None):
        background = background_color or 'background_2'
        width_class = 'width_80' if is_width_smaller else 'width_85'
        title_properties_dict = {
            "class": "summary center {width_class} padding {background}".format(
                width_class=width_class, background=background),
        }
        section_properties_dict = {}
        if is_expandable:
            title_properties_dict["onclick"] = "hideShowElement(event.target.nextElementSibling)"
            section_properties_dict["class"] = "details"
        title_element = HTMLBuilder.create_element('div', [title], title_properties_dict)
        section_element = HTMLBuilder.create_element('div', [sub_section_element], section_properties_dict)
        container_element = HTMLBuilder.create_element('div', [title_element, section_element])
        return container_element

    @staticmethod
    def create_element(tag_name, content_items_list, properties_dict=None):
        properties_str = ""
        if properties_dict:
            for property_name in properties_dict:
                properties_str += " {property_name}=\"{property_value}\"".format(
                    property_name=property_name,
                    property_value=properties_dict[property_name]
                )
        tag_str = "<{tag_name}{properties_str}>{content}</{tag_name}>".format(
            tag_name=tag_name,
            properties_str=properties_str,
            content="\n".join(content_items_list))
        return tag_str

    @staticmethod
    def process_item(item):
        if item is None:
            return "---"
        if item is True:
            return HTMLBuilder.create_element('p', ['Yes'], {"style": "color:green"})
        if item is False:
            return HTMLBuilder.create_element('p', ['No'], {"style": "color:red"})
        if item == 'Passed':
            return HTMLBuilder.create_element('p', [item], {"style": "color:green"})
        if item == 'Failed':
            return HTMLBuilder.create_element('p', [item], {"style": "color:red"})
        item_str = str(item)
        htmlDetectionList = ['<table', '</table>', '<tr', '</tr>', '<td', '</td>']
        isHtml = False
        # pass html but block xml in <code> sections
        for htmlComponent in htmlDetectionList:
            if htmlComponent in item_str: isHtml = True
        if not isHtml:
            for char in ['<', '>']:
                replacement = HTMLBuilder.create_element('code', [char])
                item_str = item_str.replace(char, replacement)

        item_str = item_str.replace("\n", "<br>")
        item_str = item_str.replace("\\n", "<br>")
        item_str = item_str.replace("\t", "&emsp;")
        item_str = item_str.replace("\\t", "&emsp;")
        item_str = item_str.replace(" ", "&nbsp;")
        item_str = item_str.replace('-&nbsp;Not&nbsp;Connected',
                                    HTMLBuilder.create_element(
                                        'p', ['-&nbsp;Not&nbsp;Connected'], {"style": "color:red; display: contents;"}))
        # item_str = HTMLBuilder.change_states_colors(item_str=item_str)
        # links = re.findall(r"http[s]+:[\/\w\.+:?=\-%]+", item_str)

        if "-&nbsp;in&nbsp;maintenance" in item_str:
            item_str = item_str.replace('in&nbsp;maintenance',
                                        '<span style="color: red; font-weight: bold;">in&nbsp;maintenance</span>')

        all_links_iter = re.finditer(r"http[s]+:[\/\w\.+:?=\-%~&]+", item_str)

        for links_iter in all_links_iter:
            link = links_iter.group(0)
            # Remove "&nbsp" and "&emsp" from the link, to keep it together with the ";" as an HTML space and tab - Fix for a bug (ICET-2085)
            link = link.replace("&nbsp", "")
            link = link.replace("&emsp", "")
            clickable_link = HTMLBuilder.create_element('a', [link], {
                'href': link,
                'target': '_blank'
            })

            # replace only the nth accurnce
            where = links_iter.start()
            before = item_str[:where]
            after = item_str[where:]
            after = after.replace(link, clickable_link, 1)
            item_str = before + after

            # item_str = item_str.replace(link, clickable_link)
        return item_str

    @staticmethod
    def change_states_colors(item_str):
        for state, color in list(States.get_states_colors_dict().items()):
            if item_str is state:
                return HTMLBuilder.create_element('p', [item_str], {"style": "color:{}".format(color)})
            results = re.findall(r"&nbsp;{}:&nbsp;\d+".format(state), item_str)
            if results:
                item_str = item_str.replace(
                    results[0], HTMLBuilder.create_element('p', [results[0]],
                                                           {"style": "color:{}; display: contents;".format(color)}))
        return item_str

    @staticmethod
    def get_row_details_element(colspan, items_list, details_properties_dict=None):
        properties_dict = {"colspan": colspan, "style": "text-align : start;"}
        if details_properties_dict:
            properties_dict.update(details_properties_dict)
        cell_details_element = HTMLBuilder.create_element('td', items_list, properties_dict)
        row_details_element = HTMLBuilder.create_element('tr', [cell_details_element], {"class": "details"})
        return row_details_element

    @staticmethod
    def get_details_link_cell_element():
        return HTMLBuilder.create_element('td', ['details...'], {
            "onclick": "hideShowElement(event.target.parentElement.nextElementSibling)", "class": "summary"})

    @staticmethod
    def create_host_details_by_click_cell(item, item_id, is_equal=True, properties_dict=None, msg='Having different values among hosts'):
        if not properties_dict:
            properties_dict = {}
        text = item

        if type(item) is dict and len(item) > 0:
            short_text = HTMLBuilder.get_list_in_nice_format(list(item.keys()))

            text = HTMLBuilder._get_cell_text(item)

            first_time_present = "{}<br><font color='blue'>{} - <br>double click for more details</font>".format(str(short_text), msg)
            short_text = "{}<br><font color=\\'blue\\'>{} - <br>double click for more details</font>".format(str(short_text), msg)
            if not is_equal:
                first_time_present = HTMLBuilder.create_element('b', [first_time_present], {"style": "color:red;"})
                short_text = "<b style=\\'color:red;\\'>" + str(short_text) + "</b>"
            properties_dict.update({'title': '', 'id': item_id,
                                    'ondblclick': "changeText(event, '{}', '{}', {})".format(text, short_text, {"textAlign": 'left'})})

            return HTMLBuilder.create_element('td', [first_time_present], properties_dict)

        if type(item) is list:
            text = HTMLBuilder.get_list_in_nice_format(item)
        if not is_equal:
            text = HTMLBuilder.create_element('b', [str(text)], {"style": "color:red;"})
            return HTMLBuilder.create_element('td', [text], properties_dict)
        return HTMLBuilder.create_element('td', [str(text)], properties_dict)

    @staticmethod
    def _get_cell_text(item):
        text = ""
        for key, val in list(item.items()):
            nice_key = HTMLBuilder._get_nice_str(key)
            nice_val = HTMLBuilder._get_nice_str(val)
            if type(nice_val) is str:
                text += "{}:<br>  {}<br>".format(nice_key, nice_val)
            elif type(nice_val) is list:
                nice_val = "<br>    ".join(val)
                nice_val = "<pre>    " + nice_val + "</pre>"
                text += "{}:<br>  {}<br>".format(nice_key, nice_val)
            elif isinstance(nice_val, dict) or isinstance(nice_val, OrderedDict):
                new_text = HTMLBuilder._get_cell_text(nice_val)
                text += "{}:<br>".format(new_text)
        return text

    @staticmethod
    def get_list_in_nice_format(list_items):
        res = ""

        for item in list_items:
            nice_item = HTMLBuilder._get_nice_str(item)
            res += "{}<br>".format(nice_item)

        return res

    @staticmethod
    def _get_nice_str(item):
        if type(item) is str:
            return item.replace("[", "").replace("]", "").replace(",", "").replace("u'", "").replace("'", ""). \
                replace("{", "").replace("}", "")
        return item

    @staticmethod
    def create_cell(item, is_title=False, colspan=None, process_item=True, properties_dict=None):
        help_text = ""
        text = item
        if not properties_dict:
            properties_dict = {}
        if type(item) is list and len(item) == 2:
            text = item[0]
            help_text = item[1]
        properties_dict['title'] = help_text
        if colspan:
            properties_dict["colspan"] = colspan
        if is_title:
            properties_dict["class"] = "middle_font light_background"
            return HTMLBuilder.create_element('th', [text], properties_dict)
        else:
            item_str = text
            if process_item:
                item_str = HTMLBuilder.process_item(text)
            return HTMLBuilder.create_element('td', [item_str], properties_dict)

    @staticmethod
    def create_table_with_details_last_row(title, header_row, rows, unique_name_list=None,
                                           link_to_information_validation_list=None, collapse_table_with_header=False,
                                           title_element_properties={"class": "center width_90 middle_font"}):
        details_properties_dict = None
        if link_to_information_validation_list:
            assert (len(link_to_information_validation_list) == len(rows)), \
                "Expect to get the same range of 'rows' and 'link_to_information_validation_list'"
        row_details_element_list = []
        for i, row_cells in enumerate(rows):
            details_last_row = HTMLBuilder.process_item(row_cells[-1])
            details_list = [details_last_row]
            if link_to_information_validation_list:
                details_list = [HTMLBuilder.add_link_to_information_validation(
                    link_to_information_validation_list[i][0], link_to_information_validation_list[i][1]) +
                                details_last_row]
            if details_list[0] == "":
                if len(details_list) == 1:
                    return HTMLBuilder.create_table(title=title, header_row=header_row, rows=rows,
                                                    collapse_table_with_header=collapse_table_with_header,
                                                    title_element_properties=title_element_properties)
                else:
                    details_list = details_list[1:]
            if unique_name_list and unique_name_list[i]:
                details_properties_dict = {"class": unique_name_list[i].replace(" ", "_")}
            row_details_element = HTMLBuilder.get_row_details_element(len(header_row), details_list, details_properties_dict)
            row_details_element_list.append(row_details_element)
        return HTMLBuilder.create_table(
            title=title, header_row=header_row, rows=rows, collapse_table_with_header=collapse_table_with_header,
            row_details_element_list=row_details_element_list, title_element_properties=title_element_properties)

    @staticmethod
    def create_information_table_list(info_dict):
        table_element_properties = {"class": "width_90 center"}
        header_row = ['Host', 'Information']
        elements_list = []
        for info_id, unique_name in enumerate(info_dict):
            title = list(info_dict[unique_name].values())[0].get(ResultKeys.DESCRIPTION_TITLE)
            rows = info_dict[unique_name]
            table_title_element = ""
            if title:
                link = list(info_dict[unique_name].values())[0].get(ResultKeys.DOCUMENTATION_LINK)
                if link:
                    title = HTMLBuilder.create_element('a', [title], {'href': link, 'style': 'color:dodgerblue;', 'target': '_blank'})
                table_title_element = HTMLBuilder.create_table_title_element(
                    title=title,
                    title_properties_dict={"class": "center width_90 padding background_5 {}".format(
                        str(unique_name.replace(" ", "_")))})
            rows_elements_list = []
            header_row_element = HTMLBuilder.create_header_row_element(header_row)
            inner_tables_elements_list = []
            tables_elements_list = [table_title_element]
            if header_row_element:
                rows_elements_list.append(header_row_element)
            for i, (row_key, value) in enumerate(rows.items()):
                if value.get(ResultKeys.TABLE_SYSTEM_INFO):
                    inner_tables_elements_list.append(HTMLBuilder.create_element(
                        'div', [HTMLBuilder.create_information_inner_table(row_key, value, table_element_properties)]))
                else:
                    rows_elements_list.append(HTMLBuilder.create_information_row(info_id, row_key, i, value))
            if len(rows_elements_list) > 1:
                table_element = HTMLBuilder.create_element('table', rows_elements_list, table_element_properties)
                tables_elements_list.append(table_element)
            if inner_tables_elements_list:
                tables_elements_list.extend(inner_tables_elements_list)
            table_with_title = HTMLBuilder.create_element('div', tables_elements_list)
            elements_list.append(table_with_title)
        return elements_list

    @staticmethod
    def create_information_inner_table(host_name, value, table_element_properties):
        inner_table_rows_elements_list = []
        table_system_info = value.get(ResultKeys.TABLE_SYSTEM_INFO)
        table = table_system_info.get(ResultKeys.TABLE)
        inner_table_colspan = len(table[0])
        if value.get(ResultKeys.SYSTEM_INFO):
            first_header = HTMLBuilder.create_element(
                'td', [HTMLBuilder.process_item(value.get(ResultKeys.SYSTEM_INFO))], {"colspan": inner_table_colspan})
            inner_table_rows_elements_list.append(first_header)
        header_row = table_system_info.get(ResultKeys.HEADERS, []) if table_system_info.get(ResultKeys.HEADERS) else []
        if value.get(ResultKeys.PRINT_HOST_AS_TITLE):
            inner_table_title_element = HTMLBuilder.create_table_title_element(HTMLBuilder.process_item(host_name))
        else:
            inner_table_title_element = ""
        header_row_element = HTMLBuilder.create_header_row_element(header_row)
        if header_row_element:
            inner_table_rows_elements_list.append(header_row_element)
        rows_list = HTMLBuilder.get_information_inner_table_rows_list(table_system_info)
        for i, row_cells in enumerate(rows_list[0:6]):
            inner_table_rows_elements_list.extend(HTMLBuilder.create_row_table(i, row_cells))
        if len(rows_list) > 6:
            button_element = HTMLBuilder.create_element(
                'button', ["show more"], {"class": "show-more-less-button", "onclick": "showMoreLess(event, {})".format(
                    str(json.dumps(rows_list)).replace("'", "\\'").replace('"', "'"))})
            button_cell = HTMLBuilder.create_cell(item=button_element, process_item=False, colspan=inner_table_colspan)
            inner_table_rows_elements_list.append(HTMLBuilder.create_element('tr', [button_cell]))
        if table_system_info.get(ResultKeys.REMARKS):
            remark_cell = HTMLBuilder.create_cell(item=table_system_info.get(ResultKeys.REMARKS),
                                                  colspan=inner_table_colspan)
            inner_table_rows_elements_list.append(HTMLBuilder.create_element('tr', [remark_cell]))
        table_element = HTMLBuilder.create_element('table', inner_table_rows_elements_list, table_element_properties)
        return HTMLBuilder.create_element('div', [inner_table_title_element, table_element])

    @staticmethod
    def get_information_inner_table_rows_list(table_system_info):
        table = table_system_info.get(ResultKeys.TABLE)
        rows_list = []
        for i in range(len(table)):
            rows_list.append([])
            for column_number in range(len(table[i])):
                cell = table[i][column_number]
                cell_value = list(cell.keys())[0]
                cell_color = States.get_states_colors_dict()[cell[cell_value]]
                rows_list[i].append({cell_value: {"style": "color:{}".format(cell_color)}})
        return rows_list

    @staticmethod
    def create_information_row(info_id, host_name, i, value):
        cells_elements_list = []
        cells_elements_list.append(HTMLBuilder.create_cell(host_name))
        info_iter_id = 'info_{}_{}'.format(info_id, i)
        text = value.get(ResultKeys.SYSTEM_INFO)
        short_text = text
        short_text_len = 150
        if len(text) > short_text_len:
            short_text = text[:short_text_len]
            if text[short_text_len] != ' ':
                short_text += text[short_text_len:].split()[0]
        if short_text != text:
            short_text = short_text.replace("'", "\\'").replace('"', "\\'").strip().replace('\n', "<br>")
            text = text.replace("'", "\\'").replace('"', "\\'").strip().replace('\n', "<br>")
            first_time_present = short_text + "<br><font color='blue'>click for more details</font>"
            short_text_link = short_text + "<br><font color=\\'blue\\'>click for more details</font>"
            properties_dict = {'title': '', 'id': info_iter_id, 'style': 'text-align: center;',
                               'onclick': "changeText(event, '{}', '{}')".format(str(text), short_text_link)}
            cells_elements_list.append(HTMLBuilder.create_cell(item=first_time_present, process_item=False,
                                                               properties_dict=properties_dict))
        else:
            cells_elements_list.append(HTMLBuilder.create_cell(text))
        row_element = HTMLBuilder.create_element('tr', cells_elements_list)
        return row_element

    @staticmethod
    def create_table(title, header_row, rows, collapse_table_with_header=False, row_details_element_list=None,
                     title_element_properties={"class": "center width_90 middle_font"}):
        table_title_element = ""
        if title:
            table_title_element = HTMLBuilder.create_table_title_element(title, collapse_table_with_header,
                                                                         title_element_properties)
        rows_elements_list = []
        header_row_element = HTMLBuilder.create_header_row_element(header_row)
        if header_row_element:
            rows_elements_list.append(header_row_element)
        for i, row_cells in enumerate(rows):
            rows_elements_list.extend(HTMLBuilder.create_row_table(i, row_cells, row_details_element_list))
        table_element = HTMLBuilder.create_element('table', rows_elements_list, {"class": "width_90 center"})
        if collapse_table_with_header:
            table_element = HTMLBuilder.create_element('div', [table_element], {'class': 'details'})
        table_with_title = HTMLBuilder.create_element('div', [table_title_element, table_element])
        return table_with_title

    @staticmethod
    def create_row_table(i, row_cells, row_details_element_list=None):
        rows_elements_list = []
        cells_elements_list = []
        row_cells_list = row_cells[0:-1] if row_details_element_list else row_cells
        for cell_item in row_cells_list:
            if type(cell_item) is dict:
                assert len(list(cell_item.keys())) == 1, \
                    "Please ensure that each dictionary in 'row_cells_list' contains exactly one key-value pair."
                cell_value = list(cell_item.keys())[0]
                properties_dict = cell_item[cell_value]
                cell_element = HTMLBuilder.create_cell(
                    list(cell_item.keys())[0], properties_dict=properties_dict, process_item=True)
            else:
                cell_element = HTMLBuilder.create_cell(cell_item)
            cells_elements_list.append(cell_element)
        row_details_element = None
        if row_details_element_list:
            row_details_element = row_details_element_list[i]
            if row_details_element:
                details_link_cell_element = HTMLBuilder.get_details_link_cell_element()
                cells_elements_list.append(details_link_cell_element)
        row_element = HTMLBuilder.create_element('tr', cells_elements_list)
        rows_elements_list.append(row_element)
        if row_details_element:
            rows_elements_list.append(row_details_element)
        return rows_elements_list

    @staticmethod
    def create_table_title_element(title, collapse_table_with_header=False,
                                   title_properties_dict={"class": "center width_90 middle_font"}):
        table_title_element = HTMLBuilder.create_element('div', [title], title_properties_dict)
        if collapse_table_with_header:
            table_title_element = HTMLBuilder.create_element('div', [table_title_element], {
                "onclick": "hideShowElement(event.target.parentElement.nextElementSibling)", "class": "summary"
            })
        return table_title_element

    @staticmethod
    def create_header_row_element(header_row, colspan=None):
        cells_list_header = []
        for item in header_row:
            cell_element = HTMLBuilder.create_cell(item, is_title=True, colspan=colspan)
            cells_list_header.append(cell_element)
        if header_row:
            return HTMLBuilder.create_element('tr', cells_list_header)
        return None

    @staticmethod
    def add_link_to_information_validation(information_validation_unique_name, is_inner_tab):
        if is_inner_tab:
            inner_tab = "true"
        else:
            inner_tab = "false"

        if information_validation_unique_name:
            on_click_event = "navigate_to_information_validation_by_link('{}', {});return false;".format(
                information_validation_unique_name.replace(" ", "_"), inner_tab)
            link = HTMLBuilder.create_element('a', ['For more information click here'], {
                "onclick": on_click_event, "href": "#"})
            return "{} <br>".format(link)
        return ""

    @staticmethod
    def create_table_by_columns(title, columns_list, rows, details_key, details_last_row, note=None):
        table_elements_list = []
        table_title_element = HTMLBuilder.create_table_title_element(title)
        table_elements_list.append(table_title_element)
        if note:
            table_note_element = HTMLBuilder.create_element('div', [note], {"class": "center width_90 small_font"})
            table_elements_list.append(table_note_element)
        colspan = len(columns_list)
        rows_elements_list = []
        columns_elements_list = []
        columns_cells_list = []
        body_elements_list = []
        for column in columns_list:
            cell_element = HTMLBuilder.create_cell(column, is_title=True)
            columns_cells_list.append(cell_element)
        columns_row_element = HTMLBuilder.create_element('tr', columns_cells_list)
        columns_elements_list.append(columns_row_element)
        header_element = HTMLBuilder.create_element('thead', columns_elements_list)
        for row in rows:
            cells_elements_list = []
            for column in columns_list:
                if column == details_key:
                    continue
                cell_element = HTMLBuilder.create_cell(row[column])
                cells_elements_list.append(cell_element)
            if details_last_row:
                item_str = HTMLBuilder.process_item(row[details_key])
                row_details_element = HTMLBuilder.get_row_details_element(colspan, [item_str])
                details_link_cell_element = HTMLBuilder.get_details_link_cell_element()
                cells_elements_list.append(details_link_cell_element)
            row_element = HTMLBuilder.create_element('tr', cells_elements_list)
            rows_elements_list.append(row_element)
            if details_last_row:
                rows_elements_list.append(row_details_element)
        body_element = HTMLBuilder.create_element('tbody', rows_elements_list)
        body_elements_list.append(body_element)
        table_element = HTMLBuilder.create_element('table', [header_element, body_element],
                                                   {"class": "width_90 center"})
        table_elements_list.append(table_element)
        table_with_title = HTMLBuilder.create_element('div', table_elements_list, {"class": "fixTableHead"})
        return table_with_title

    def add_style(self, key, property_dict):
        properties_str = ""
        for property_name in property_dict:
            properties_str += "\n\t{property_name} : {property_val};".format(
                property_name=property_name,
                property_val=property_dict[property_name]
            )
        properties_str = "{" + properties_str + "\n}"
        style_section = "\n{key} {properties_str}\n".format(
            key=key,
            properties_str=properties_str)
        self.style += style_section

    def add_element_to_body(self, element_str):
        self.body += element_str

    def build_page(self):
        html_str = """
<!DOCTYPE html>
<html>
<head>
<style>
{}
</style>
</head>
<body>
{}
{}
</body>
</html>
        """.format(self.style, self.script, self.body)
        with open(self.out_file_path, 'w') as out_file:
            out_file.write(html_str)
