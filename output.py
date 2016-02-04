from __future__ import division

import os
import sys
import shutil
import itertools

from jinja2 import Environment, FileSystemLoader

import cluster


class View:
    def __init__(self, name, pdiff, ftypes, gopts):    
        self.name = name
        self.data = { 'type':self.name, 'title':'gDelta '+ self.name }
        self.files = {}
        self.paths = {}
        for ftype in ftypes:
            filename = self.get_file_base(pdiff) + '.' + ftype
            self.files[ftype] = filename 
            self.paths[ftype] = os.path.join(gopts.out_dir, filename)
        
    def get_file_base(self, pdiff):
        return "{0}_{1}-{2}_{3}_{4}".format(pdiff.grammar_name, 
                                            pdiff.prev_grammar.version, 
                                            pdiff.new_grammar.version,
                                            pdiff.profile_alias,
                                            self.name)
        

def parse_status(foo, prev, new):
    # foo is an uneeded argument added by jinja2
    if prev in (0, -1):
        prev_parse = False
    else:
        prev_parse = True
    if new in (0, -1):
        new_parse = False
    else:
        new_parse = True

    if prev_parse and new_parse:
        if prev == new:
            s = "same_readings"
        else:
            s = "change_in_readings"
    elif not prev_parse and not new_parse:
            s = "no_parse"
    elif prev_parse and not new_parse:
        s = "now_no_parse"        
    elif not prev_parse and new_parse:
        s = "now_parses"
    return s


class Output:
    ftypes = ('html',)
    static_dir = 'static'
    css_files = ['gdelta.css']
    image_files = [
        'sort.gif',
        'ascending.gif',
        'descending.gif',
        'first.png',
        'last.png',
        'next.png',
        'prev.png'
        ]
    js_files = [
        'jquery-1.10.2.min.js', 
        'jquery.tablesorter.js',
        'tablesorter_filter.js',
        'jquery.tablesorter.pager.js',
        'gdelta.js', 
        ]
    static_files = image_files + js_files + css_files

    def __init__(self, pdiff, gopts):
        self.pdiff = pdiff
        self.gopts = gopts      
        self.env = Environment(loader=FileSystemLoader(
                os.path.join(gopts.script_dir, 'html')))

        view_types = [
            ('summary', self.add_summary_data),
            ('attributes', self.add_attributes_data), 
            ('clusters', self.add_clusters_data),
            ('items', self.add_items_data), 
            ('errors', self.add_errors_data)
        ]

        self.views = []
        for view_name, data_func in view_types: 
            if not self.gopts.clustering and view_name == 'clusters':  
                continue
            view = View(view_name, pdiff, self.ftypes, gopts)
            self.views.append(view)
            data_func(view.data)
        self.common_data = self.get_common_data()

    def check_out_dir(self):
        if not os.path.isdir(self.gopts.out_dir):
            os.makedirs(self.gopts.out_dir)
        static_path = os.path.join(self.gopts.out_dir, self.static_dir)
        if not os.path.isdir(static_path): 
            os.makedirs(static_path)

    def copy_static_files(self):
        for sfile in self.static_files:
            original_path = os.path.join(self.gopts.script_dir, 'html', sfile) 
            output_path = os.path.join(self.gopts.out_dir, self.static_dir, 
                                       sfile)
            shutil.copyfile(original_path, output_path)

    def get_common_data(self):
        for parse_cat in self.pdiff.parse_cats:
            parse_cat.html_heading = parse_cat.title.replace(
                '->', '&rarr;').replace('*parse*', '<u>parse</u>')
            parse_cat.top_attributes = sorted(
                parse_cat.attribute_counts.keys(), 
                key=lambda x:parse_cat.attribute_counts[x], 
                reverse=True)

        data = {
            'views' : self.views,
            'static_dir' : self.static_dir,
            'js_files' : self.js_files,
            'css_files' : self.css_files,
            'gram_name' : self.pdiff.grammar_name,
            'prev_gram' : self.pdiff.prev_grammar,
            'new_gram' : self.pdiff.new_grammar,
            'parse_cats' : self.pdiff.parse_cats,
            'attributes' : self.pdiff.attributes 
            }

        for view in self.views:
            data[view.name+'_view'] = view
        return data

    def add_summary_data(self, data):
        self.env.filters['parse_status'] = parse_status
        data['profile_names'] = ", ".join(self.pdiff.profile_names)
        data['num_profiles'] = len(self.pdiff.profile_names)
        data['num_prev_feats'] = sum(1 for f in 
                                     self.pdiff.attributes.values() 
                                     if f.prev_counts != 0)
        data['num_new_feats'] = sum(1 for f in 
                                    self.pdiff.attributes.values() 
                                    if f.new_counts != 0)
        data['num_items'] = self.pdiff.num_items
        data['num_errors_prev'] = self.pdiff.prev_errors
        data['num_errors_new'] = self.pdiff.new_errors
        data['prev_parsing_items'] = self.pdiff.prev_parsing_items
        data['new_parsing_items'] = self.pdiff.new_parsing_items
        data['prev_coverage'] = 100 * (self.pdiff.prev_parsing_items 
                                       / self.pdiff.num_items)
        data['new_coverage'] = 100 * (self.pdiff.new_parsing_items 
                                      / self.pdiff.num_items)
        data['prev_readings'] = self.pdiff.prev_readings
        data['new_readings'] = self.pdiff.new_readings
        data['av_prev_readings'] = ( self.pdiff.prev_readings 
                                     / self.pdiff.num_items )
        data['av_new_readings'] = ( self.pdiff.new_readings 
                                    / self.pdiff.num_items )
        data['av_prev_parse_readings'] = ( self.pdiff.prev_readings 
                                           / self.pdiff.prev_parsing_items )
        data['av_new_parse_readings'] = ( self.pdiff.new_readings 
                                          / self.pdiff.new_parsing_items )
        data['still_parses_prev'] = self.pdiff.still_parses_prev
        data['still_parses_new'] = self.pdiff.still_parses_new
        data['now_parses'] = self.pdiff.now_parses
        data['now_no_parse'] = self.pdiff.now_no_parse
        data['top_attributes'] = self.get_top_attribute_changes(20)

    def get_top_attribute_changes(self, num_tops):
        top_increases = sorted(self.pdiff.attributes.values(), 
                               key=lambda x:x.change, 
                               reverse=True)[:num_tops]
        top_decreases = sorted(self.pdiff.attributes.values(), 
                               key=lambda x:x.change)[:num_tops]
        return itertools.izip_longest(top_increases, top_decreases, 
                                      fillvalue=None)

    def add_attributes_data(self, data):
        data['sorted_attributes'] = sorted(self.pdiff.attributes.values(),
                                key=lambda x:x.change_size, reverse=True)

    def add_errors_data(self, data):
        self.pdiff.error_list.sort(key=lambda x:x.id)
        data['errors'] = self.pdiff.error_list

    def add_items_data(self, data):
        self.pdiff.item_list.sort(key=lambda x:x[0].id)
        data['item_list'] = self.pdiff.item_list
               
    def add_clusters_data(self, data):
        for parse_cat in self.pdiff.parse_cats:
            results = parse_cat.results         
            if results is None:
               continue
            if len(results.clusters) <= 1:
                continue
            for cluster in results.clusters:
                cluster.points.sort(key=lambda x:x.silhouette, reverse=True)
                top_feats = sorted(cluster.nearest_point.item.attributes, 
                                   key=lambda x:self.pdiff.attributes[x].cluster_weight, 
                                   reverse=True)[:5]
                metrics = cluster.get_metrics(top_feats, results.clusters)
                cluster.top_attributes = []
                for f,c,o in metrics:
                    cluster.top_attributes.append({
                            'name':f,
                            'weight':self.pdiff.attributes[f].cluster_weight, 
                            'cohesion':int(round(100*c)), 
                            'overlap':int(round(100*o))
                            })

    def do_output(self):
        self.check_out_dir()
        self.copy_static_files()
        for view in self.views:
            view.data.update(self.common_data)
            for ftype in self.ftypes:
                template = view.name + '.' + ftype
                output = self.env.get_template(template).render(view.data)
                with open(view.paths[ftype], 'w') as f:
                    f.write(output.encode('utf-8'))
        
