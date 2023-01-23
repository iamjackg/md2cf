from typing import Dict

import rich.live
import rich.progress
import rich.table
import rich.text
import rich.tree

from md2cf.console_output import console


class Md2cfTUI(object):
    def __init__(self, pages_to_upload):
        tree = rich.tree.Tree("Pages to upload", hide_root=True)
        progress_table = rich.table.Table.grid()
        progress_table.row_styles = ["dim", ""]
        title_to_tree: Dict[str, rich.tree.Tree] = dict()
        self.title_to_progress: Dict[str, rich.progress.Progress] = dict()
        for page in pages_to_upload:
            if page.file_path is None and len(pages_to_upload) > 1:
                pretty_title = f":open_file_folder: {page.title}"
            else:
                pretty_title = f":page_facing_up: {page.title}"

            page_progress = rich.progress.Progress(
                rich.progress.BarColumn(),
                rich.progress.SpinnerColumn(finished_text=""),
                rich.progress.TextColumn(""),
                console=console,
            )
            page_progress.add_task(
                description="", total=1 + len(page.attachments), start=False
            )
            self.title_to_progress[page.title] = page_progress

            if page.parent_title:
                try:
                    page_node = title_to_tree[page.parent_title].add(
                        pretty_title, style="bright"
                    )
                except KeyError:
                    continue
            else:
                page_node = tree.add(pretty_title, style="bright")

            progress_table.add_row(page_progress)
            title_to_tree[page.title] = page_node

            for attachment in page.attachments:
                page_node.add(f":paperclip: {attachment}", style="dim")
                attachment_progress = rich.progress.Progress(
                    rich.progress.BarColumn(),
                    rich.progress.SpinnerColumn(finished_text="done"),
                    rich.progress.TextColumn(""),
                    console=console,
                )
                attachment_progress.add_task(description="", total=1, start=False)
                progress_table.add_row(attachment_progress)
                self.title_to_progress[
                    f"{page.title} {attachment}"
                ] = attachment_progress
        self.overall_progress = rich.progress.Progress(console=console)
        self.overall_progress.add_task(
            "Total progress",
            start=True,
            total=len(pages_to_upload)
            + sum([len(page.attachments) for page in pages_to_upload]),
        )
        table = rich.table.Table().grid(padding=1, pad_edge=True)
        tree_and_progress = rich.table.Table.grid(
            "", rich.table.Column(""), expand=True
        )
        tree_and_progress.add_row(tree, progress_table)
        table.add_row(tree_and_progress)
        table.add_row(self.overall_progress)
        self.live = rich.live.Live(table, console=console, refresh_per_second=10)
        # return self.overall_progress, overall_task, table, self.title_to_progress

    def __enter__(self):
        self.live.__enter__()
        return self

    def __exit__(
        self,
        *args,
        **kwargs,
    ):
        self.live.__exit__(*args, **kwargs)

    def set_item_progress_label(self, item_name, label):
        self.title_to_progress[item_name].columns[2].text_format = label

    def set_item_finished_text(self, item_name, finished_text):
        self.title_to_progress[item_name].columns[1].finished_text = finished_text

    def set_item_finished_text_from_result(self, item_name, upsert_result):
        self.set_item_finished_text(
            item_name, Md2cfTUI.format_upsert_result(upsert_result)
        )

    def tick_item_progress(self, item_name):
        task_for_this_item = self.title_to_progress[item_name].task_ids[0]
        self.title_to_progress[item_name].update(
            task_id=task_for_this_item,
            advance=1,
        )

    def tick_global_progress(self):
        self.overall_progress.update(
            task_id=self.overall_progress.task_ids[0], advance=1
        )

    def start_item_task(self, item_name):
        task_for_this_item = self.title_to_progress[item_name].task_ids[0]
        self.title_to_progress[item_name].start_task(task_id=task_for_this_item)

    def reset_item_task(self, item_name, total):
        task_for_this_item = self.title_to_progress[item_name].task_ids[0]
        self.title_to_progress[item_name].reset(task_id=task_for_this_item, total=total)

    @staticmethod
    def format_upsert_result(upsert_item_result):
        if upsert_item_result.action == upsert_item_result.action.CREATED:
            finished_text = rich.text.Text.from_markup(
                "[green]:heavy_check_mark-emoji: Created"
            )
        elif upsert_item_result.action == upsert_item_result.action.UPDATED:
            finished_text = rich.text.Text.from_markup(
                "[green]:heavy_check_mark-emoji: Updated"
            )
        elif upsert_item_result.action == upsert_item_result.action.SKIPPED:
            finished_text = rich.text.Text.from_markup("[yellow]No change")

        return finished_text
