/*
 * Copyright (C) 2007, 2008, 2009 Rodney Cryderman <rcryderman@gmail.com>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301  USA.
 *
*/

#include "misc.h"
#include <glib/gi18n.h>
#include <gtk/gtk.h>
#include <libdesktop-agnostic/gtk.h>
#include <libdesktop-agnostic/vfs.h>

#include "cairo-menu-applet.h"


/*TODO
 Leaking a few strings related to the "activate" data.
 */

static GtkWidget * _get_recent_menu (GtkWidget * menu);
static gboolean _update_recent_menu (GtkWidget * menu);


DesktopAgnosticFDODesktopEntry *
get_desktop_entry (gchar * desktop_file)
{
  DesktopAgnosticVFSFile *file;
  DesktopAgnosticFDODesktopEntry *entry;
  GError * error = NULL;
  file = desktop_agnostic_vfs_file_new_for_path (desktop_file, &error);
  if (error)
  {
    g_critical ("Error when trying to load the launcher: %s", error->message);
    g_error_free (error);
    return NULL;
  }

  if (file == NULL || !desktop_agnostic_vfs_file_exists (file))
  {
    if (file)
    {
      g_object_unref (file);
    }
    g_critical ("File not found: '%s'", desktop_file);
    return NULL;
  }

  entry = desktop_agnostic_fdo_desktop_entry_new_for_file (file, &error);

  g_object_unref (file);
  if (error)
  {
    g_critical ("Error when trying to load the launcher: %s", error->message);
    g_error_free (error);
    return NULL;
  }
  return entry;
}

void
_launch (GtkMenuItem *menu_item,gchar * desktop_file)
{
  DesktopAgnosticFDODesktopEntry *entry;
  GError * error = NULL;
  
  entry = get_desktop_entry (desktop_file);
  
  if (entry == NULL)
  {
    return;
  }

  if (!desktop_agnostic_fdo_desktop_entry_key_exists (entry,"Exec"))
  {
    return;
  }

  desktop_agnostic_fdo_desktop_entry_launch (entry,0, NULL, &error);
  if (error)
  {
    g_critical ("Error when launching: %s", error->message);
    g_error_free (error);
  }

  g_object_unref (entry);
}

GtkWidget *
get_gtk_image (const gchar const * icon_name)
{
  GtkWidget *image = NULL;
  GdkPixbuf *pbuf;  
  gint width,height;
  
  if (icon_name)
  {
    gtk_icon_size_lookup (GTK_ICON_SIZE_MENU,&width,&height);
    /*TODO Need to listen for icon theme changes*/
    if ( gtk_icon_theme_has_icon (gtk_icon_theme_get_default(),icon_name) )
    {
      image = gtk_image_new_from_icon_name (icon_name,GTK_ICON_SIZE_MENU);
    }
    
    if (!image)
    {
      if (!pbuf)
      {
        pbuf = gdk_pixbuf_new_from_file_at_scale (icon_name,
                                         -1,
                                         height,
                                         TRUE,
                                         NULL);
      }
      
      if (pbuf)
      {
        image = gtk_image_new_from_pixbuf (pbuf);
        g_object_unref (pbuf);        
      }
    }
  }
 
  return image;
}

void
_exec (GtkMenuItem *menuitem,gchar * cmd)
{
  g_debug ("executing %s",cmd);
  g_spawn_command_line_async (cmd,NULL);
}

void 
_fillin_connected(DesktopAgnosticVFSVolume *volume,CairoMenu *menu)
{
  GtkWidget *item;
  DesktopAgnosticVFSFile *uri;
  const gchar *uri_str;
  GtkWidget * image;
  gchar * exec;
  
  g_message("Attempting to add %s...", desktop_agnostic_vfs_volume_get_name(volume));

  /* don't use g_return_if_fail because it runs g_critical */
  if (!desktop_agnostic_vfs_volume_is_mounted(volume))
  {
    return;
  }

  item = cairo_menu_item_new();
  gtk_menu_item_set_label (GTK_MENU_ITEM(item),desktop_agnostic_vfs_volume_get_name(volume));
  image = get_gtk_image ( desktop_agnostic_vfs_volume_get_icon(volume));
  if (image)
  {
    gtk_image_menu_item_set_image (GTK_IMAGE_MENU_ITEM (item),image);
  }
  
  uri = desktop_agnostic_vfs_volume_get_uri(volume);
  uri_str = desktop_agnostic_vfs_file_get_uri(uri);
  g_object_unref(uri);
  exec = g_strdup_printf("%s %s", XDG_OPEN, uri_str);
  g_signal_connect(G_OBJECT(item), "activate", G_CALLBACK(_exec), exec);  
  g_object_weak_ref (G_OBJECT(item),(GWeakNotify) g_free,exec);  
  gtk_menu_shell_append(GTK_MENU_SHELL(menu),item);
}

void
_remove_menu_item  (GtkWidget *menu_item,GtkWidget * menu)
{
  gtk_container_remove (GTK_CONTAINER(menu),menu_item);
}

static void
_queue_get_recent_menu (GtkRecentManager *recent_manager,
                                             GtkWidget *menu) 
{
  /*This is currently a bit pointless*/
  g_idle_add ((GSourceFunc)_update_recent_menu,menu);
}

static gboolean
_update_recent_menu (GtkWidget * menu)
{
  _get_recent_menu (menu);
  return FALSE;
}

static GtkWidget * 
_get_recent_menu (GtkWidget * menu)
{  
  static gboolean done_once = FALSE;
  GtkRecentManager *recent = gtk_recent_manager_get_default ();
  GtkWidget * menu_item;
  GList * recent_list;
  GList * iter;
  gint width,height;

  gtk_container_foreach (GTK_CONTAINER (menu),(GtkCallback)_remove_menu_item,menu);  
  gtk_icon_size_lookup (GTK_ICON_SIZE_MENU,&width,&height);
  recent_list = gtk_recent_manager_get_items (recent);
  if (recent_list)
  {
    for (iter = recent_list; iter; iter = iter->next)
    {
      if (gtk_recent_info_get_age(iter->data) <=2)
      {
        gchar * app_name = gtk_recent_info_last_application (iter->data);
        GdkPixbuf * pbuf = NULL;
        GtkWidget * image = NULL;
        const gchar * app_exec=NULL;
        guint count;
        time_t time_;
        const gchar * txt = gtk_recent_info_get_display_name (iter->data);
        menu_item = cairo_menu_item_new_with_label (txt);

        pbuf = gtk_recent_info_get_icon (iter->data,height);
        if (pbuf)
        {
          image = gtk_image_new_from_pixbuf (pbuf);
          g_object_unref (pbuf);
        }
        if (image)
        {
          gtk_image_menu_item_set_image (GTK_IMAGE_MENU_ITEM (menu_item),image);          
        }
        if (gtk_recent_info_get_application_info (iter->data,app_name,
                                                         &app_exec,
                                                         &count,
                                                         &time_))
        {
          gchar * exec = g_strdup_printf ("%s %s",app_exec,
                                          gtk_recent_info_get_uri (iter->data));
          g_signal_connect(G_OBJECT(menu_item), "activate", G_CALLBACK(_exec), exec);
          g_object_weak_ref (G_OBJECT(menu_item),(GWeakNotify) g_free,exec);          
        }
        gtk_menu_shell_append(GTK_MENU_SHELL(menu),menu_item);
        g_free (app_name);
      }
    }
  }

  g_list_foreach (recent_list, (GFunc)gtk_recent_info_unref,NULL);
  g_list_free (recent_list);
  gtk_widget_show_all (menu); 
  g_signal_handlers_disconnect_by_func (recent,G_CALLBACK(_queue_get_recent_menu),menu);
  g_signal_connect (recent,"changed",G_CALLBACK(_queue_get_recent_menu),menu);

  done_once = TRUE;
  return menu;
}

GtkWidget * 
get_recent_menu (void)
{
  GtkWidget *menu = cairo_menu_new();
  return _get_recent_menu (menu);
}

MenuInstance *
get_menu_instance ( AwnApplet * applet,
                                  GetRunCmdFunc run_cmd_fn,
                                  GetSearchCmdFunc search_cmd_fn,
                                  gchar * submenu_name,
                                  gint flags)
{
  MenuInstance *instance = g_malloc (sizeof (MenuInstance));
  instance->applet = applet;
  instance->run_cmd_fn = run_cmd_fn;
  instance->search_cmd_fn = search_cmd_fn;
  instance->flags = flags;
  instance->done_once = FALSE;
  instance->places=NULL;
  instance->recent=NULL;
  instance->menu = NULL; 
  instance->submenu_name = g_strdup(submenu_name);
  return instance;
}

