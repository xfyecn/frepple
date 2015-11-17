#
# Copyright (C) 2007-2013 by frePPLe bvba
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from django.conf.urls import patterns, url, include

import freppledb.common.views
import freppledb.common.serializers
import freppledb.common.dashboard

from freppledb.common.api.views import APIIndexView


# Automatically add these URLs when the application is installed
autodiscover = True

urlpatterns = patterns(
  # Prefix
  '',

  # User preferences
  (r'^preferences/$', freppledb.common.views.preferences),

  # Horizon updates
  (r'^horizon/$', freppledb.common.views.horizon),

  # Dashboard widgets
  (r'^widget/(.+)/', freppledb.common.dashboard.Dashboard.dispatch),

  # Model list reports, which override standard admin screens
  (r'^data/auth/group/$', freppledb.common.views.GroupList.as_view()),
  (r'^data/common/user/$', freppledb.common.views.UserList.as_view()),
  (r'^data/common/bucket/$', freppledb.common.views.BucketList.as_view()),
  (r'^data/common/bucketdetail/$', freppledb.common.views.BucketDetailList.as_view()),
  (r'^data/common/parameter/$', freppledb.common.views.ParameterList.as_view()),
  (r'^data/common/comment/$', freppledb.common.views.CommentList.as_view()),
  (r'^comments/([^/]+)/([^/]+)/(.+)/$', freppledb.common.views.Comments),

  (r'^detail/([^/]+)/([^/]+)/(.+)/$', freppledb.common.views.detail),

  # REST API framework
#  (r'^api/$', freppledb.common.serializers.BucketAPI.as_view()),
  (r'^api/common/bucket/$', freppledb.common.serializers.BucketAPI.as_view()),
  (r'^api/common/bucketdetail/$', freppledb.common.serializers.BucketDetailAPI.as_view()),
  (r'^api/common/parameter/$', freppledb.common.serializers.ParameterAPI.as_view()),
  (r'^api/common/comment/$', freppledb.common.serializers.CommentAPI.as_view()),

  (r'^api/common/bucket/(?P<pk>(.+))/$', freppledb.common.serializers.BucketdetailAPI.as_view()),
  (r'^api/common/bucketdetail/(?P<pk>(.+))/$', freppledb.common.serializers.BucketDetaildetailAPI.as_view()),
  (r'^api/common/parameter/(?P<pk>(.+))/$', freppledb.common.serializers.ParameterdetailAPI.as_view()),
  (r'^api/common/comment/(?P<pk>(.+))/$', freppledb.common.serializers.CommentdetailAPI.as_view()),
  (r'^api/$', APIIndexView),

 # two factor authentication for cloud
  (r'^accounts/', include('registration.backends.default.urls')),
)
