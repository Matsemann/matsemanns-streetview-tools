from matsemanns_streetview_tools.video import _create_ffmpeg_frame_file_content


def test_create_ffmpeg_frame_file_content():
    result = _create_ffmpeg_frame_file_content([5,100, 1000])

    expected = """select='+eq(n,5)
+eq(n,100)
+eq(n,1000)'"""

    assert result == expected
